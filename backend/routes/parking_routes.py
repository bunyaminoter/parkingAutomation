"""
Parking routes - Parking records CRUD, manual entry, image/video upload
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks, Body
from sqlalchemy.orm import Session
from datetime import datetime
import os

from backend.database import SessionLocal
from backend import models, crud
from backend.services.plate_recognition import recognize_plate_from_bytes
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/api", tags=["parking"])

MIN_PLATE_CONFIDENCE = float(os.getenv("PLATE_MIN_CONFIDENCE", "0.8"))
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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


@router.get("/parking_records")
def get_parking_records(db: Session = Depends(get_db)):
    """Tüm park kayıtlarını listele"""
    return get_serialized_records(db)


@router.get("/parking_records/{record_id}")
def get_parking_record(record_id: int, db: Session = Depends(get_db)):
    """Tekil park kaydı getir"""
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")
    
    return serialize_record(record)


@router.get("/parking_records/by_plate/{plate_number}")
def get_parking_records_by_plate(plate_number: str, db: Session = Depends(get_db)):
    """Belirli bir plaka için tüm kayıtları getir"""
    records = crud.get_records_by_plate(db, plate_number)
    return [serialize_record(r) for r in records]


@router.post("/parking_records")
def create_parking_record(
    plate_number: str = Form(...),
    confidence: float | None = Form(None),
    db: Session = Depends(get_db)
):
    """Yeni park kaydı oluştur"""
    record = models.ParkingRecord(
        plate_number=plate_number,
        entry_time=datetime.utcnow(),
        confidence=confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize_record(record)


@router.put("/parking_records/{record_id}/exit")
def complete_parking_record(
    background_tasks: BackgroundTasks,
    record_id: int, 
    fee: float = None,
    db: Session = Depends(get_db)
):
    """Park kaydını tamamla (çıkış işlemi)"""
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
        time_diff = exit_time - record.entry_time
        total_minutes = round(time_diff.total_seconds() / 60)
        fee_per_minute = 2.0
        calculated_fee = max(total_minutes * fee_per_minute, 2.0)  # Minimum 2 TL
        record.fee = calculated_fee
    else:
        record.fee = fee
    
    db.commit()
    db.refresh(record)
    
    response = serialize_record(record)
    
    # WebSocket broadcast için background task ekle
    if background_tasks:
        from backend.routes.websocket_routes import broadcast_latest_records
        background_tasks.add_task(broadcast_latest_records)
    
    return response


@router.put("/parking_records/{record_id}/plate")
def update_parking_record_plate(
    background_tasks: BackgroundTasks,
    record_id: int,
    plate_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Park kaydının plaka numarasını güncelle"""
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")
    
    plate_number = plate_data.get("plate_number", "").strip()
    if not plate_number:
        raise HTTPException(status_code=400, detail="Plaka numarası boş olamaz")
    
    record.plate_number = plate_number
    db.commit()
    db.refresh(record)
    
    response = serialize_record(record)
    
    # WebSocket broadcast için background task ekle
    if background_tasks:
        from backend.routes.websocket_routes import broadcast_latest_records
        background_tasks.add_task(broadcast_latest_records)
    
    return response


@router.delete("/parking_records/{record_id}")
def delete_parking_record(
    background_tasks: BackgroundTasks,
    record_id: int,
    db: Session = Depends(get_db)
):
    """Park kaydını sil"""
    record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Park kaydı bulunamadı")
    
    db.delete(record)
    db.commit()
    
    # WebSocket broadcast için background task ekle
    if background_tasks:
        from backend.routes.websocket_routes import broadcast_latest_records
        background_tasks.add_task(broadcast_latest_records)
    
    return {"success": True, "message": "Kayıt silindi"}


@router.post("/manual_entry")
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
                from backend.routes.websocket_routes import broadcast_latest_records
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
        from backend.routes.websocket_routes import broadcast_latest_records
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


@router.post("/upload/image")
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
                    from backend.routes.websocket_routes import broadcast_latest_records
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

    # 6) Opsiyonel: yüklenen dosyayı diske kaydet
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        path = os.path.join(UPLOAD_DIR, safe_name)
        with open(path, "wb") as f:
            f.write(content)
    except Exception:
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
        from backend.routes.websocket_routes import broadcast_latest_records
        background_tasks.add_task(broadcast_latest_records)

    return response

