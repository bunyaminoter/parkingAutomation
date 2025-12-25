from sqlalchemy import Column, Integer, String, DateTime, Float, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import enum


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


class Vehicle(Base):
    """Araç modeli - Plaka bilgisi ile"""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parking_records = relationship("ParkingRecord", back_populates="vehicle")


class PaymentStatus(enum.Enum):
    """Payment status enum"""
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(64), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="TRY")
    status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)
    parking_record_id = Column(Integer, ForeignKey("parking_records.id"), nullable=True, index=True)
    receiver_name = Column(String(255), nullable=False, default="La Parque A.Ş.")
    iban = Column(String(34), nullable=False)
    merchant_code = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    parking_record = relationship(
        "ParkingRecord", 
        back_populates="payment",
        foreign_keys=[parking_record_id]
    )


class ParkingRecord(Base):
    __tablename__ = "parking_records"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(32), nullable=False, index=True)  # Backward compatibility için
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True, index=True)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    fee = Column(Float, default=0.0)
    confidence = Column(Float, nullable=True)
    payment_id = Column(Integer, nullable=True, index=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="parking_records", foreign_keys=[vehicle_id])
    payment = relationship(
        "Payment",
        back_populates="parking_record",
        foreign_keys=[Payment.parking_record_id]
    )
