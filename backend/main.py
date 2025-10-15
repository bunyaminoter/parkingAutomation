from fastapi import FastAPI, Form, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import shutil
import os
from backend.services.plate_recognition import recognize_plate_from_bytes
from backend.database import SessionLocal, engine
from backend import models

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
# 🔹 Manuel plaka girişi (sadece plaka)
# --------------------------------------------------
@app.post("/api/manual_entry")
def manual_entry(
    plate_number: str = Form(...),
    db: Session = Depends(get_db)
):
    # Park kaydı oluştur (sadece plaka ile)
    record = models.ParkingRecord(
        plate_number=plate_number, 
        entry_time=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee
    }

# --------------------------------------------------
# 🔹 Plaka tanıma için resim yükleme
# --------------------------------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload/image")
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
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

    # 3) Park kaydı oluştur (Car tablosu yoksa doğrudan parking_records içine plate yaz)
    try:
        record = models.ParkingRecord(
            plate_number=plate,
            entry_time=datetime.utcnow()
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

    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee,
        "confidence": conf
    }

# --------------------------------------------------
# 🔹 Plaka tanıma için video yükleme
# --------------------------------------------------
@app.post("/api/upload/video")
def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Plaka tanıma servisini kullan
        from backend.services.plate_recognition import recognize_plate_from_video
        content = file.file.read()
        plate_number = recognize_plate_from_video(content)
        
        if not plate_number:
            raise HTTPException(status_code=400, detail="Plaka tanınamadı")
        
        # Park kaydı oluştur
        record = models.ParkingRecord(
            plate_number=plate_number,
            entry_time=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return {
            "id": record.id,
            "plate_number": record.plate_number,
            "entry_time": record.entry_time,
            "exit_time": record.exit_time,
            "fee": record.fee
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video işleme hatası: {str(e)}")

# --------------------------------------------------
# 🔹 Tüm park kayıtlarını listeleme
# --------------------------------------------------
@app.get("/api/parking_records")
def get_parking_records(db: Session = Depends(get_db)):
    records = db.query(models.ParkingRecord).order_by(models.ParkingRecord.entry_time.desc()).all()
    results = []
    for r in records:
        results.append({
            "id": r.id,
            "plate_number": r.plate_number,
            "entry_time": r.entry_time,
            "exit_time": r.exit_time,
            "fee": r.fee
        })
    return results

# --------------------------------------------------
# 🔹 Çıkış işlemi (park kaydını tamamlama)
# --------------------------------------------------
@app.put("/api/parking_records/{record_id}/exit")
def complete_parking_record(
    record_id: int, 
    fee: float = 0.0,
    db: Session = Depends(get_db)
):
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")
    
    if record.exit_time:
        raise HTTPException(status_code=400, detail="Bu kayıt zaten tamamlanmış")
    
    record.exit_time = datetime.utcnow()
    record.fee = fee
    db.commit()
    db.refresh(record)
    
    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "entry_time": record.entry_time,
        "exit_time": record.exit_time,
        "fee": record.fee
    }

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
        "fee": record.fee
    }

# --------------------------------------------------
# 🔹 Frontend dosyalarını sun (React build sonrası)
# --------------------------------------------------
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/", response_class=HTMLResponse)
def root_index():
    return "<html><head><meta http-equiv='refresh' content='0; url=/frontend/index.html' /></head><body></body></html>"
