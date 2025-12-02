from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import session_scope
from .. import schemas, crud
from ..services.plate_recognition import recognize_plate_from_bytes
from fastapi import BackgroundTasks
from datetime import datetime


router = APIRouter(prefix="/api", tags=["parking"])


def get_db():
    # Ortak wrapped session kullan
    with session_scope() as db:
        yield db


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Veritabanı bağlantısını test eder"""
    try:
        # Basit bir SQL sorgusu çalıştırarak veritabanı bağlantısını test et
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@router.post("/parking_records", response_model=schemas.ParkingRecordResponse)
def create_record(record: schemas.ParkingRecordCreate, db: Session = Depends(get_db)):
    return crud.create_parking_record(db, record)


@router.put("/parking_records/{record_id}/exit", response_model=schemas.ParkingRecordResponse)
def complete_record(record_id: int, fee: float | None = None, db: Session = Depends(get_db)):
    # fee=None olduğunda otomatik hesaplama yapılacak
    updated = crud.update_exit_time(db, record_id, fee=fee)
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")
    return updated


@router.get("/parking_records", response_model=list[schemas.ParkingRecordResponse])
def list_records(db: Session = Depends(get_db)):
    return crud.get_all_records(db)


# Manual plate entry
@router.post("/manual_entry", response_model=schemas.ParkingRecordResponse)
def manual_entry(
    background_tasks: BackgroundTasks,
    plate_number: str = Form(...),
    confidence: float | None = Form(None),
    db: Session = Depends(get_db),
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
        return recent_entry
    
    # 2. Aktif kayıt (çıkış yapılmamış) var mı kontrol et
    active_record = crud.get_active_record_by_plate(db, plate_number)
    
    if active_record:
        # Aktif kayıt varsa, çıkış yap
        exit_record = crud.exit_parking_by_plate(db, plate_number)
        if exit_record:
            return exit_record
    
    # 3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    record = crud.create_parking_record(
        db, 
        schemas.ParkingRecordCreate(
            plate_number=plate_number,
            confidence=confidence
        )
    )
    return record


@router.post("/upload/image", response_model=schemas.ParkingRecordResponse)
async def upload_image(
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
    content = await file.read()
    plate, conf = recognize_plate_from_bytes(content, lang_list=["tr","en"], gpu=False)
    if not plate:
        raise HTTPException(status_code=400, detail="Plate could not be recognized")
    
    # 1. Son 10 saniye içinde giriş yapılmış mı kontrol et (debounce)
    recent_entry = crud.get_recent_entry_by_plate(db, plate, seconds=10)
    if recent_entry:
        # Araç kameranın önünde bekliyor, yeni giriş yapma
        return recent_entry
    
    # 2. Aktif kayıt (çıkış yapılmamış) var mı kontrol et
    active_record = crud.get_active_record_by_plate(db, plate)
    
    if active_record:
        # Aktif kayıt varsa, çıkış yap
        exit_record = crud.exit_parking_by_plate(db, plate)
        if exit_record:
            return exit_record
    
    # 3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    return crud.create_parking_record(
        db, 
        schemas.ParkingRecordCreate(
            plate_number=plate,
            confidence=conf
        )
    )


@router.post("/upload/video", response_model=schemas.ParkingRecordResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Video yükleme ve plaka tanıma:
    1. Son 10 saniye içinde aynı plaka için giriş yapılmışsa, yeni giriş yapma (araç bekliyor)
    2. Aktif kayıt (exit_time=None) varsa, çıkış yap
    3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    """
    content = await file.read()
    # Video için ilk frame'i al ve plaka tanıma yap (basit yaklaşım)
    # Daha gelişmiş bir yaklaşım için video'dan frame'ler çıkarılabilir
    plate, conf = recognize_plate_from_bytes(content, lang_list=["tr","en"], gpu=False)
    if not plate:
        raise HTTPException(status_code=400, detail="Plate could not be recognized")
    
    # 1. Son 10 saniye içinde giriş yapılmış mı kontrol et (debounce)
    recent_entry = crud.get_recent_entry_by_plate(db, plate, seconds=10)
    if recent_entry:
        # Araç kameranın önünde bekliyor, yeni giriş yapma
        return recent_entry
    
    # 2. Aktif kayıt (çıkış yapılmamış) var mı kontrol et
    active_record = crud.get_active_record_by_plate(db, plate)
    
    if active_record:
        # Aktif kayıt varsa, çıkış yap
        exit_record = crud.exit_parking_by_plate(db, plate)
        if exit_record:
            return exit_record
    
    # 3. Aktif kayıt yoksa, yeni giriş kaydı oluştur
    return crud.create_parking_record(
        db, 
        schemas.ParkingRecordCreate(
            plate_number=plate,
            confidence=conf
        )
    )


