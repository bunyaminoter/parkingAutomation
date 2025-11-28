from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


def calculate_fee(entry_time: datetime, exit_time: datetime) -> float:
    """
    Giriş ve çıkış zamanı arasındaki farkı hesaplayıp ücreti belirler.
    Dakika başına 2 TL ücret alır.
    
    Args:
        entry_time: Giriş zamanı
        exit_time: Çıkış zamanı
    
    Returns:
        float: Hesaplanan ücret (TL)
    """
    # Zaman farkını hesapla
    time_diff = exit_time - entry_time
    
    # Toplam dakikayı hesapla
    total_minutes = time_diff.total_seconds() / 60
    
    # Dakika başına 2 TL ücret
    fee_per_minute = 2.0
    
    # Ücreti hesapla
    total_fee = total_minutes * fee_per_minute
    
    # Minimum ücret 2 TL (1 dakika)
    return max(total_fee, 2.0)


# ParkingRecord operations
def create_parking_record(db: Session, record: schemas.ParkingRecordCreate) -> models.ParkingRecord:
    db_record = models.ParkingRecord(
        plate_number=record.plate_number,
        entry_time=record.entry_time or datetime.utcnow(),
        exit_time=record.exit_time,
        fee=record.fee or 0.0,
        confidence=record.confidence,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def update_exit_time(db: Session, record_id: int, exit_time: Optional[datetime] = None, fee: Optional[float] = None) -> Optional[models.ParkingRecord]:
    db_record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not db_record:
        return None
    
    # Çıkış zamanını ayarla
    exit_time = exit_time or datetime.utcnow()
    db_record.exit_time = exit_time
    
    # Eğer fee belirtilmemişse, otomatik hesapla
    if fee is None:
        calculated_fee = calculate_fee(db_record.entry_time, exit_time)
        db_record.fee = calculated_fee
    else:
        db_record.fee = fee
    
    db.commit()
    db.refresh(db_record)
    return db_record


def get_all_records(db: Session) -> List[models.ParkingRecord]:
    return db.query(models.ParkingRecord).order_by(models.ParkingRecord.entry_time.desc()).all()

