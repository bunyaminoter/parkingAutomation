from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import SessionLocal
from .. import schemas, crud
from ..services.plate_recognition import (
    recognize_plate_from_image,
    recognize_plate_from_video,
)


router = APIRouter(prefix="/api", tags=["parking"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    plate_number: str = Form(...),
    db: Session = Depends(get_db),
):
    record = crud.create_parking_record(db, schemas.ParkingRecordCreate(plate_number=plate_number))
    return record


@router.post("/upload/image", response_model=schemas.ParkingRecordResponse)
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    plate = recognize_plate_from_image(content)
    if not plate:
        raise HTTPException(status_code=400, detail="Plate could not be recognized")
    return crud.create_parking_record(db, schemas.ParkingRecordCreate(plate_number=plate))


@router.post("/upload/video", response_model=schemas.ParkingRecordResponse)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    plate = recognize_plate_from_video(content)
    if not plate:
        raise HTTPException(status_code=400, detail="Plate could not be recognized")
    return crud.create_parking_record(db, schemas.ParkingRecordCreate(plate_number=plate))


