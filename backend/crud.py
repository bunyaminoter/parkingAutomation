from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


# ParkingRecord operations
def create_parking_record(db: Session, record: schemas.ParkingRecordCreate) -> models.ParkingRecord:
    db_record = models.ParkingRecord(
        plate_number=record.plate_number,
        entry_time=record.entry_time or datetime.utcnow(),
        exit_time=record.exit_time,
        fee=record.fee or 0.0,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def update_exit_time(db: Session, record_id: int, exit_time: Optional[datetime] = None, fee: Optional[float] = None) -> Optional[models.ParkingRecord]:
    db_record = db.query(models.ParkingRecord).filter(models.ParkingRecord.id == record_id).first()
    if not db_record:
        return None
    db_record.exit_time = exit_time or datetime.utcnow()
    if fee is not None:
        db_record.fee = fee
    db.commit()
    db.refresh(db_record)
    return db_record


def get_all_records(db: Session) -> List[models.ParkingRecord]:
    return db.query(models.ParkingRecord).order_by(models.ParkingRecord.entry_time.desc()).all()

