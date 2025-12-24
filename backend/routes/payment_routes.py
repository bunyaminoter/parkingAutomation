"""
Payment routes - Ödeme işlemleri ve QR kod yönetimi
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import logging

from backend.database import SessionLocal
from backend import models
from backend import schemas
from backend import crud
from backend.services.qr_service import create_qr_content, create_qr_json
from backend.services.barrier_service import BarrierService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["payments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/payments", response_model=schemas.PaymentResponse)
def create_payment(
    payment_data: schemas.PaymentCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Yeni ödeme kaydı oluşturur (çıkış yaparken)
    """
    try:
        payment = crud.create_payment(
            db=db,
            amount=payment_data.amount,
            currency=payment_data.currency,
            parking_record_id=payment_data.parking_record_id
        )
        
        logger.info(f"Payment created: ID={payment.id}, Reference={payment.reference}, Amount={payment.amount} {payment.currency}")
        
        return payment
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ödeme kaydı oluşturulamadı: {str(e)}")


@router.get("/payments/{payment_id}/qr", response_model=schemas.QRContentResponse)
def get_payment_qr(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    Ödeme için QR içeriğini döner
    """
    payment = crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Ödeme kaydı bulunamadı")
    
    if payment.status != models.PaymentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Bu ödeme zaten {payment.status.value} durumunda. QR sadece PENDING ödemeler için oluşturulabilir."
        )
    
    qr_data = create_qr_content(payment)
    qr_json = create_qr_json(payment)
    
    return {
        "qr_data": qr_data,
        "qr_json": qr_json,
        "payment_id": payment.id,
        "reference": payment.reference
    }


@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    Ödemeyi onaylar (test/simülasyon için)
    Bu endpoint ödeme tamamlandığını simüle eder.
    """
    payment = crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Ödeme kaydı bulunamadı")
    
    if payment.status == models.PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Bu ödeme zaten tamamlanmış")
    
    if payment.status == models.PaymentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Bu ödeme iptal edilmiş")
    
    # Ödeme durumunu PAID yap
    updated_payment = crud.update_payment_status(
        db=db,
        payment_id=payment_id,
        status=models.PaymentStatus.PAID
    )
    
    logger.info(f"Payment confirmed: ID={payment_id}, Reference={updated_payment.reference}")
    
    # Bariyeri aç
    try:
        await BarrierService.open_barrier(updated_payment)
        
        # Park kaydını güncelle (eğer varsa)
        if updated_payment.parking_record_id:
            parking_record = db.query(models.ParkingRecord).filter(
                models.ParkingRecord.id == updated_payment.parking_record_id
            ).first()
            if parking_record:
                parking_record.payment_id = updated_payment.id
                db.commit()
        
        return {
            "success": True,
            "message": "Ödeme tamamlandı ve bariyer açıldı",
            "payment": {
                "id": updated_payment.id,
                "reference": updated_payment.reference,
                "status": updated_payment.status.value,
                "amount": updated_payment.amount,
                "currency": updated_payment.currency
            }
        }
    except ValueError as e:
        logger.error(f"Barrier error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/{payment_id}", response_model=schemas.PaymentResponse)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Ödeme kaydını getirir"""
    payment = crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Ödeme kaydı bulunamadı")
    return payment


@router.post("/payments/{payment_id}/auto-confirm")
async def auto_confirm_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    Otomatik ödeme onayı (30 saniye sonra)
    QR gösterildikten sonra otomatik olarak ödemeyi tamamlar
    """
    payment = crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Ödeme kaydı bulunamadı")
    
    if payment.status != models.PaymentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Bu ödeme zaten {payment.status.value} durumunda"
        )
    
    logger.info(f"Auto-confirm started for payment {payment_id}. Will confirm in 30 seconds...")
    
    # 30 saniye bekle
    await asyncio.sleep(30)
    
    # Ödemeyi onayla
    return await confirm_payment(payment_id, db)

