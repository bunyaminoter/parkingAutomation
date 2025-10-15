from sqlalchemy import Column, Integer, String, DateTime, Float
from .database import Base
from datetime import datetime


class ParkingRecord(Base):
    __tablename__ = "parking_records"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(32), nullable=False, index=True)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    fee = Column(Float, default=0.0)
