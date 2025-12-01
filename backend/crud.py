from datetime import datetime, timedelta
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


def get_active_record_by_plate(db: Session, plate_number: str) -> Optional[models.ParkingRecord]:
    """
    Belirli bir plaka için aktif (çıkış yapılmamış) kayıt bulur.
    
    Args:
        db: Veritabanı session'ı
        plate_number: Plaka numarası
    
    Returns:
        Aktif kayıt varsa ParkingRecord, yoksa None
    """
    return db.query(models.ParkingRecord).filter(
        models.ParkingRecord.plate_number == plate_number,
        models.ParkingRecord.exit_time.is_(None)
    ).order_by(models.ParkingRecord.entry_time.desc()).first()


def exit_parking_by_plate(db: Session, plate_number: str, exit_time: Optional[datetime] = None, fee: Optional[float] = None) -> Optional[models.ParkingRecord]:
    """
    Plaka numarasına göre aktif kaydı çıkış yapar.
    
    Args:
        db: Veritabanı session'ı
        plate_number: Plaka numarası
        exit_time: Çıkış zamanı (None ise şu anki zaman kullanılır)
        fee: Ücret (None ise otomatik hesaplanır)
    
    Returns:
        Güncellenmiş kayıt veya None (aktif kayıt yoksa)
    """
    active_record = get_active_record_by_plate(db, plate_number)
    if not active_record:
        return None
    
    return update_exit_time(db, active_record.id, exit_time=exit_time, fee=fee)


def get_recent_entry_by_plate(db: Session, plate_number: str, seconds: int = 30) -> Optional[models.ParkingRecord]:
    """
    Kısa süre içinde (varsayılan 10 saniye) aynı plaka için giriş yapılmış mı kontrol eder.
    Bu, aracın kameranın önünde beklediği durumları tespit etmek için kullanılır.
    
    Args:
        db: Veritabanı session'ı
        plate_number: Plaka numarası
        seconds: Kontrol edilecek süre (saniye cinsinden)
    
    Returns:
        Son giriş kaydı varsa ParkingRecord, yoksa None
    """
    threshold_time = datetime.utcnow() - timedelta(seconds=seconds)
    return db.query(models.ParkingRecord).filter(
        models.ParkingRecord.plate_number == plate_number,
        models.ParkingRecord.entry_time >= threshold_time
    ).order_by(models.ParkingRecord.entry_time.desc()).first()

