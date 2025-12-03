"""
User page routes - Public user endpoints (no authentication required)
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
import os

from backend.database import SessionLocal
from backend.services.plate_recognition import recognize_plate_from_bytes

router = APIRouter(prefix="/api/user", tags=["user-page"])

MIN_PLATE_CONFIDENCE = float(os.getenv("PLATE_MIN_CONFIDENCE", "0.8"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/recognize_plate")
def user_recognize_plate(file: UploadFile = File(...)):
    """Kullanıcı sayfası için sadece plaka tanıma (veritabanına kaydetmez)"""
    # 1) Dosya içeriğini oku
    try:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Boş dosya gönderildi")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {str(e)}")

    # 2) Plaka tanımaya gönder
    plate, conf = recognize_plate_from_bytes(content, lang_list=["tr","en"], gpu=False)

    if not plate:
        raise HTTPException(status_code=400, detail="Plaka tanınamadı")
    if conf < MIN_PLATE_CONFIDENCE:
        raise HTTPException(status_code=400, detail="Güven oranı yetersiz")

    return {
        "plate_number": plate,
        "confidence": conf,
        "message": "Plaka başarıyla tanındı"
    }

