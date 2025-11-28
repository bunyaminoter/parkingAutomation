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
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import os
import hashlib
from typing import Set
from backend.services.plate_recognition import recognize_plate_from_bytes
from backend.database import SessionLocal, engine, ensure_schema
from backend import models

ensure_schema()

MIN_PLATE_CONFIDENCE = float(os.getenv("PLATE_MIN_CONFIDENCE", "0.8"))

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
# 🔹 DB session bağımlılığı
# --------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    db = SessionLocal()
    try:
        payload = get_serialized_records(db)
    finally:
        db.close()
    await manager.broadcast({"type": "records", "payload": payload})


async def send_initial_snapshot(websocket: WebSocket):
    db = SessionLocal()
    try:
        payload = get_serialized_records(db)
    finally:
        db.close()
    await websocket.send_json({"type": "records", "payload": payload})

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
# 🔹 Authentication endpoints
# --------------------------------------------------
@app.post("/api/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Admin girişi"""
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    # Kullanıcıyı kontrol et
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.password == hashed_password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")
    
    return {
        "success": True,
        "message": "Giriş başarılı",
        "user": {
            "id": user.id,
            "username": user.username
        }
    }

@app.get("/api/user_login")
def user_login():
    """Kullanıcı girişi (şifre gerektirmez)"""
    return {
        "success": True,
        "message": "Kullanıcı girişi başarılı",
        "user_type": "user"
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
    # Park kaydı oluştur (sadece plaka ile)
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

    # 3) Park kaydı oluştur (Car tablosu yoksa doğrudan parking_records içine plate yaz)
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

    # 4) Opsiyonel: yüklenen dosyayı diske kaydet (isteğe bağlı)
    try:
        import os
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
        "confidence": conf
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
