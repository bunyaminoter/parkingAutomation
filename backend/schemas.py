from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ParkingRecordBase(BaseModel):
    plate_number: str = Field(..., min_length=2, max_length=32)
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    fee: Optional[float] = 0.0
    confidence: Optional[float] = None


class ParkingRecordCreate(ParkingRecordBase):
    plate_number: str = Field(..., min_length=2, max_length=32)
    entry_time: Optional[datetime] = None


class ParkingRecordResponse(ParkingRecordBase):
    id: int

    class Config:
        from_attributes = True


# Payment Schemas
class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0, description="Ödeme tutarı")
    currency: str = Field(default="TRY", max_length=3, description="Para birimi")
    parking_record_id: Optional[int] = None


class PaymentCreate(PaymentBase):
    """Ödeme oluşturma için schema"""
    pass


class PaymentResponse(BaseModel):
    id: int
    reference: str
    amount: float
    currency: str
    status: str
    parking_record_id: Optional[int]
    receiver_name: str
    iban: str
    merchant_code: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QRContentResponse(BaseModel):
    """QR içeriği response"""
    qr_data: dict
    qr_json: str
    payment_id: int
    reference: str


class PaymentConfirmRequest(BaseModel):
    """Ödeme onaylama için schema"""
    payment_id: int



