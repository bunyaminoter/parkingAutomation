from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import os
import hashlib
import secrets
from typing import Set, Optional, List
from pydantic import BaseModel
from backend.services.plate_recognition import recognize_plate_from_bytes
from backend.database import SessionLocal, engine, ensure_schema, session_scope
from backend import models, crud

ensure_schema()

MIN_PLATE_CONFIDENCE = float(os.getenv("PLATE_MIN_CONFIDENCE", "0.8"))

# Session yönetimi için in-memory storage (production'da Redis kullanılabilir)
active_sessions: dict[str, dict] = {}
SESSION_COOKIE_NAME = "parking_session_token"
SESSION_DURATION_DAYS = 7  # "Beni hatırla" için
SESSION_DURATION_HOURS = 24  # Normal session için

# --------------------------------------------------
# 🔹 Veritabanı tabloları migrasyon ile oluşturulur
# --------------------------------------------------
# models.Base.metadata.create_all(bind=engine)  # Migrasyon kullanıyoruz

# --------------------------------------------------
# 🔹 Uygulama nesnesi oluştur
# --------------------------------------------------
app = FastAPI(title="Parking Automation API", version="1.0.0")

# --------------------------------------------------
# 🔹 CORS ayarları (React erişimi için)
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000" , "http://localhost:8000"
 ,"http://127.0.0.1:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# 🔹 DB session bağımlılığı (wrapped session kullanır)
# --------------------------------------------------
def get_db():
    # Tüm controller'larda aynı wrapped session kullanılsın diye
    with session_scope() as db:
        # FastAPI Depends mekanizması için yield gerekiyor
        yield db


def serialize_record(record: models.ParkingRecord):
    return jsonable_encoder(
        {
            "id": record.id,
            "plate_number": record.plate_number,
            "entry_time": record.entry_time,
            "exit_time": record.exit_time,
            "fee": record.fee,
            "confidence": record.confidence,
        }
    )


def get_serialized_records(db: Session):
    records = db.query(models.ParkingRecord).order_by(models.ParkingRecord.entry_time.desc()).all()
    return [serialize_record(r) for r in records]


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        to_remove = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                to_remove.append(connection)
        for connection in to_remove:
            self.disconnect(connection)


manager = ConnectionManager()


async def broadcast_latest_records():
    # Wrapped session ile kayıtları çek
    with session_scope() as db:
        payload = get_serialized_records(db)
    await manager.broadcast({"type": "records", "payload": payload})


async def send_initial_snapshot(websocket: WebSocket):
    # Wrapped session ile ilk snapshot'ı gönder
    with session_scope() as db:
        payload = get_serialized_records(db)
    await websocket.send_json({"type": "records", "payload": payload})


# --------------------------------------------------
# 🔹 Admin / kullanıcı yönetimi için şema modelleri
# --------------------------------------------------


class PlateUpdate(BaseModel):
    plate_number: str


class UserOut(BaseModel):
    id: int
    username: str
    is_super_admin: int
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordUpdate(BaseModel):
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    is_super_admin: int = 0


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    is_super_admin: Optional[int] = None

# --------------------------------------------------
# 🔹 Health check endpoint
# --------------------------------------------------
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Veritabanı bağlantısını test eder"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

# --------------------------------------------------
# 🔹 Session yönetimi yardımcı fonksiyonları
# --------------------------------------------------
def create_session_token(
    user_id: int,
    username: str,
    is_super_admin: int,
    remember_me: bool = False,
) -> str:
    """Yeni session token oluşturur"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + (
        timedelta(days=SESSION_DURATION_DAYS) if remember_me 
        else timedelta(hours=SESSION_DURATION_HOURS)
    )
    active_sessions[token] = {
        "user_id": user_id,
        "username": username,
        "is_super_admin": int(is_super_admin),
        "expires_at": expires_at,
        "remember_me": remember_me,
    }
    return token


def get_session_user(token: str) -> Optional[dict]:
    """Session token'dan kullanıcı bilgisini alır"""
    if token not in active_sessions:
        return None
    
    session = active_sessions[token]
    if datetime.utcnow() > session["expires_at"]:
        # Süresi dolmuş session'ı temizle
        del active_sessions[token]
        return None
    
    return session


def delete_session(token: str):
    """Session'ı siler"""
    if token in active_sessions:
        del active_sessions[token]


# --------------------------------------------------
# 🔹 Authentication endpoints
# --------------------------------------------------
@app.post("/api/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Normal admin girişi - cookie ve session token oluşturur"""
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    # Kullanıcıyı kontrol et
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.password == hashed_password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")
    
    # Sadece normal adminler bu endpoint ile giriş yapabilir
    if int(getattr(user, "is_super_admin", 0)) == 1:
        raise HTTPException(status_code=403, detail="Bu kullanıcı için normal admin girişi kullanılamaz")

    # Session token oluştur
    session_token = create_session_token(
        user.id,
        user.username,
        is_super_admin=int(getattr(user, "is_super_admin", 0)),
        remember_me=remember_me,
    )
    
    # Cookie ayarları
    # remember_me=True ise uzun süreli cookie, False ise session cookie (tarayıcı kapanınca silinir)
    if remember_me:
        max_age = SESSION_DURATION_DAYS * 24 * 60 * 60
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age,
            httponly=True,
            samesite="lax",
            secure=False  # HTTPS kullanıyorsanız True yapın
        )
    else:
        # Session cookie - tarayıcı kapanınca silinir (max_age belirtilmez)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False  # HTTPS kullanıyorsanız True yapın
        )
    
    return {
        "success": True,
        "message": "Giriş başarılı",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_super_admin": int(getattr(user, "is_super_admin", 0)),
        }
    }


@app.get("/api/check_session")
def check_session(request: Request, db: Session = Depends(get_db)):
    """Mevcut session'ı kontrol eder"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Session bulunamadı")
    
    session = get_session_user(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session geçersiz veya süresi dolmuş")
    
    # Kullanıcıyı veritabanından al
    user = db.query(models.User).filter(models.User.id == session["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "is_super_admin": int(getattr(user, "is_super_admin", 0)),
        },
        "remember_me": session.get("remember_me", False),  # remember_me bilgisini döndür
    }


@app.post("/api/logout")
def logout(response: Response, request: Request):
    """Çıkış yapar ve session'ı siler"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)
    
    # Cookie'yi sil
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    
    return {"success": True, "message": "Çıkış başarılı"}

@app.get("/api/user_login")
def user_login():
    """Kullanıcı girişi (şifre gerektirmez)"""
    return {
        "success": True,
        "message": "Kullanıcı girişi başarılı",
        "user_type": "user"
    }


# --------------------------------------------------
# 🔹 Üst admin login endpoint'i
# --------------------------------------------------
@app.post("/api/super_admin/login")
def super_admin_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Üst admin girişi - sadece is_super_admin=1 kullanıcılar"""
    hashed_password = hashlib.md5(password.encode()).hexdigest()

    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.password == hashed_password,
        models.User.is_super_admin == 1,
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz üst admin bilgileri")

    session_token = create_session_token(
        user.id,
        user.username,
        is_super_admin=1,
        remember_me=False,
    )

    # Üst admin için de aynı session cookie kullanıyoruz
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )

    return {
        "success": True,
        "message": "Üst admin girişi başarılı",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_super_admin": 1,
        },
    }

# --------------------------------------------------
# 🔹 Kullanıcı sayfası için sadece plaka algılama
# --------------------------------------------------
@app.post("/api/user/recognize_plate")
def user_recognize_plate(file: UploadFile = File(...)):
    """Kullanıcı sayfası için sadece plaka tanıma (veritabanına kaydetmez)"""
    # 1) Dosya içeriğini oku
    try:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Boş dosya gönderildi")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {str(e)}")

    # 2) Plaka tanımaya gönder
    plate, conf = recognize_plate_from_bytes(content, lang_list=["tr","en"], gpu=False)

    if not plate:
        raise HTTPException(status_code=400, detail="Plaka tanınamadı")
    if conf < MIN_PLATE_CONFIDENCE:
        raise HTTPException(status_code=400, detail="Güven oranı yetersiz")

    return {
        "plate_number": plate,
        "confidence": conf,
        "message": "Plaka başarıyla tanındı"
    }

# --------------------------------------------------
# 🔹 Manuel plaka girişi (sadece plaka)
# --------------------------------------------------
@app.post("/api/manual_entry")
def manual_entry(
    background_tasks: BackgroundTasks,
    plate_number: str = Form(...),
    confidence: float | None = Form(None),
    db: Session = Depends(get_db)
):
    """
    Plaka tanındığında:
    1. Son 10 saniye içinde aynı plaka için giriş yapılmışsa, yeni giriş yapma (araç bekliyor)
    2. Aktif kayıt (exit_time=None) varsa, çıkış yap
    3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    """
    # 1. Son 10 saniye içinde giriş yapılmış mı kontrol et (debounce)
    recent_entry = crud.get_recent_entry_by_plate(db, plate_number, seconds=10)
    if recent_entry:
        # Araç kameranın önünde bekliyor, yeni giriş yapma
        return {
            "id": recent_entry.id,
            "plate_number": recent_entry.plate_number,
            "entry_time": recent_entry.entry_time,
            "exit_time": recent_entry.exit_time,
            "fee": recent_entry.fee,
            "confidence": recent_entry.confidence,
            "message": "Araç kameranın önünde bekliyor, yeni giriş yapılmadı"
        }
    
    # 2. Aktif kayıt (çıkış yapılmamış) var mı kontrol et
    active_record = crud.get_active_record_by_plate(db, plate_number)
    
    if active_record:
        # Aktif kayıt varsa, çıkış yap
        exit_record = crud.exit_parking_by_plate(db, plate_number)
        if exit_record:
            if background_tasks:
                background_tasks.add_task(broadcast_latest_records)
            return {
                "id": exit_record.id,
                "plate_number": exit_record.plate_number,
                "entry_time": exit_record.entry_time,
                "exit_time": exit_record.exit_time,
                "fee": exit_record.fee,
                "confidence": exit_record.confidence,
                "action": "exit"
            }
    
    # 3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    record = models.ParkingRecord(
        plate_number=plate_number,
        entry_time=datetime.utcnow(),
        confidence=confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if background_tasks:
        background_tasks.add_task(broadcast_latest_records)

    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee,
        "confidence": record.confidence,
        "action": "entry"
    }

# --------------------------------------------------
# 🔹 Plaka tanıma için resim yükleme
# --------------------------------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload/image")
def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Resim yükleme ve plaka tanıma:
    1. Son 10 saniye içinde aynı plaka için giriş yapılmışsa, yeni giriş yapma (araç bekliyor)
    2. Aktif kayıt (exit_time=None) varsa, çıkış yap
    3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    """
    # 1) Dosya içeriğini oku (tek sefer okunmalı)
    try:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Boş dosya gönderildi")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {str(e)}")

    # 2) Plaka tanımaya gönder
    plate, conf = recognize_plate_from_bytes(content, lang_list=["tr","en"], gpu=False)

    if not plate:
        raise HTTPException(status_code=400, detail="Plaka tanınamadı")
    if conf < MIN_PLATE_CONFIDENCE:
        raise HTTPException(status_code=400, detail="Güven oranı yetersiz")

    # 3) Son 10 saniye içinde giriş yapılmış mı kontrol et (debounce)
    recent_entry = crud.get_recent_entry_by_plate(db, plate, seconds=10)
    if recent_entry:
        # Araç kameranın önünde bekliyor, yeni giriş yapma
        response = {
            "id": recent_entry.id,
            "plate_number": recent_entry.plate_number,
            "entry_time": recent_entry.entry_time,
            "exit_time": recent_entry.exit_time,
            "fee": recent_entry.fee,
            "confidence": recent_entry.confidence,
            "message": "Araç kameranın önünde bekliyor, yeni giriş yapılmadı"
        }
        # Dosyayı kaydet
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            path = os.path.join(UPLOAD_DIR, safe_name)
            with open(path, "wb") as f:
                f.write(content)
        except Exception:
            pass
        return response
    
    # 4) Aktif kayıt (çıkış yapılmamış) var mı kontrol et
    active_record = crud.get_active_record_by_plate(db, plate)
    
    if active_record:
        # Aktif kayıt varsa, çıkış yap
        try:
            exit_record = crud.exit_parking_by_plate(db, plate)
            if exit_record:
                response = {
                    "id": exit_record.id,
                    "plate_number": exit_record.plate_number,
                    "entry_time": exit_record.entry_time,
                    "exit_time": exit_record.exit_time,
                    "fee": exit_record.fee,
                    "confidence": exit_record.confidence,
                    "action": "exit"
                }
                # Dosyayı kaydet
                try:
                    os.makedirs(UPLOAD_DIR, exist_ok=True)
                    safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                    path = os.path.join(UPLOAD_DIR, safe_name)
                    with open(path, "wb") as f:
                        f.write(content)
                except Exception:
                    pass
                
                if background_tasks:
                    background_tasks.add_task(broadcast_latest_records)
                return response
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Çıkış işlemi hatası: {str(e)}")
    
    # 5) Aktif kayıt yoksa, yeni giriş kaydı oluştur
    try:
        record = models.ParkingRecord(
            plate_number=plate,
            entry_time=datetime.utcnow(),
            confidence=conf,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Veritabanı hatası: {str(e)}")

    # 6) Opsiyonel: yüklenen dosyayı diske kaydet (isteğe bağlı)
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        path = os.path.join(UPLOAD_DIR, safe_name)
        with open(path, "wb") as f:
            f.write(content)
    except Exception:
        # kaydetme başarısızsa hata verme; sadece loglanabilir
        pass

    response = {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee,
        "confidence": conf,
        "action": "entry"
    }

    if background_tasks:
        background_tasks.add_task(broadcast_latest_records)

    return response

# --------------------------------------------------
# 🔹 Tüm park kayıtlarını listeleme
# --------------------------------------------------
@app.get("/api/parking_records")
def get_parking_records(db: Session = Depends(get_db)):
    return get_serialized_records(db)


@app.get("/api/parking_records/by_plate/{plate_number}")
def get_parking_records_by_plate(plate_number: str, db: Session = Depends(get_db)):
    """
    Belirli bir plaka için tüm park kayıtlarını listeler.
    Kullanıcı panelinde geçmiş giriş/çıkış ve ücretleri göstermek için kullanılır.
    """
    records = crud.get_records_by_plate(db, plate_number=plate_number)
    return [serialize_record(r) for r in records]

# --------------------------------------------------
# 🔹 Çıkış işlemi (park kaydını tamamlama)
# --------------------------------------------------
@app.put("/api/parking_records/{record_id}/exit")
def complete_parking_record(
    background_tasks: BackgroundTasks,
    record_id: int, 
    fee: float = None,
    db: Session = Depends(get_db)
):
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")
    
    if record.exit_time:
        raise HTTPException(status_code=400, detail="Bu kayıt zaten tamamlanmış")
    
    # Çıkış zamanını ayarla
    exit_time = datetime.utcnow()
    record.exit_time = exit_time
    
    # Eğer fee belirtilmemişse, otomatik hesapla
    if fee is None:
        # Zaman farkını hesapla
        time_diff = exit_time - record.entry_time
        total_minutes = round(time_diff.total_seconds() / 60)
        fee_per_minute = 2.0
        calculated_fee = max(total_minutes * fee_per_minute, 2.0)  # Minimum 2 TL
        record.fee = calculated_fee
    else:
        record.fee = fee
    
    db.commit()
    db.refresh(record)
    
    response = {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee
    }

    if background_tasks:
        background_tasks.add_task(broadcast_latest_records)

    return response


# --------------------------------------------------
# 🔹 Plaka güncelleme (admin panelinden düzenleme)
# --------------------------------------------------
@app.put("/api/parking_records/{record_id}/plate")
def update_parking_plate(
    record_id: int,
    payload: PlateUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")

    record.plate_number = payload.plate_number.strip()
    db.commit()
    db.refresh(record)

    if background_tasks:
        background_tasks.add_task(broadcast_latest_records)

    return serialize_record(record)


# --------------------------------------------------
# 🔹 Kullanıcı listeleme (üst admin paneli)
# --------------------------------------------------
@app.get("/api/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), request: Request = None):
    # Sadece üst adminler kullanıcı listesine erişebilir
    if request is not None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = get_session_user(token) if token else None
        if not session or int(session.get("is_super_admin", 0)) != 1:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    users = db.query(models.User).order_by(models.User.id).all()
    return users


# --------------------------------------------------
# 🔹 Kullanıcı silme (üst admin paneli)
# --------------------------------------------------
@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    request: Request = None,
):
    # Sadece üst adminler kullanıcı silebilir
    if request is not None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = get_session_user(token) if token else None
        if not session or int(session.get("is_super_admin", 0)) != 1:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    db.delete(user)
    db.commit()

    return {"success": True, "message": "Kullanıcı silindi"}


# --------------------------------------------------
# 🔹 Kullanıcı oluşturma (üst admin paneli)
# --------------------------------------------------
@app.post("/api/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    # Sadece üst adminler kullanıcı ekleyebilir
    if request is not None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = get_session_user(token) if token else None
        if not session or int(session.get("is_super_admin", 0)) != 1:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim")

    exists = db.query(models.User).filter(models.User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")

    hashed_password = hashlib.md5(payload.password.encode()).hexdigest()
    user = models.User(
        username=payload.username,
        password=hashed_password,
        is_super_admin=int(payload.is_super_admin or 0),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------
# 🔹 Kullanıcı bilgilerini güncelleme (üst admin paneli)
# --------------------------------------------------
@app.put("/api/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    # Sadece üst adminler kullanıcı güncelleyebilir
    if request is not None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = get_session_user(token) if token else None
        if not session or int(session.get("is_super_admin", 0)) != 1:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    if payload.username is not None and payload.username != user.username:
        exists = (
            db.query(models.User)
            .filter(models.User.username == payload.username, models.User.id != user_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
        user.username = payload.username

    if payload.password:
        user.password = hashlib.md5(payload.password.encode()).hexdigest()

    if payload.is_super_admin is not None:
        user.is_super_admin = int(payload.is_super_admin)

    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------
# 🔹 Kullanıcı şifresi güncelleme (üst admin paneli - eski endpoint)
# --------------------------------------------------
@app.put("/api/users/{user_id}/password")
def change_user_password(
    user_id: int,
    payload: PasswordUpdate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    # Sadece üst adminler şifre güncelleyebilir
    if request is not None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = get_session_user(token) if token else None
        if not session or int(session.get("is_super_admin", 0)) != 1:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    if not payload.password:
        raise HTTPException(status_code=400, detail="Yeni şifre boş olamaz")

    user.password = hashlib.md5(payload.password.encode()).hexdigest()
    db.commit()

    return {"success": True, "message": "Şifre güncellendi"}

# --------------------------------------------------
# 🔹 Tekil park kaydı getirme
# --------------------------------------------------
@app.get("/api/parking_records/{record_id}")
def get_parking_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")
    
    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee,
        "confidence": record.confidence,
    }


@app.websocket("/ws/parking_records")
async def parking_records_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await send_initial_snapshot(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# --------------------------------------------------
# 🔹 Frontend dosyalarını sun (React build sonrası)
# --------------------------------------------------
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/", response_class=HTMLResponse)
def root_index():
    return "<html><head><meta http-equiv='refresh' content='0; url=/frontend/index.html' /></head><body></body></html>"
