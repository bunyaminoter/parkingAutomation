from sqlalchemy import Column, Integer, String, DateTime, Float
from .database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    # 0 = normal admin, 1 = üst admin
    is_super_admin = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, nullable=False, default=0)  # 0 = kullanılmadı, 1 = kullanıldı
    created_at = Column(DateTime, default=datetime.utcnow)


class ParkingRecord(Base):
    __tablename__ = "parking_records"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(32), nullable=False, index=True)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    fee = Column(Float, default=0.0)
    confidence = Column(Float, nullable=True)
