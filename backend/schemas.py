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



