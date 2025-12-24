"""
QR Code Service - QR içeriği üretme
"""
import json
import logging
from typing import Dict, Optional
from backend.models import Payment

logger = logging.getLogger(__name__)

# Sabitler
RECEIVER_NAME = "La Parque A.Ş."
MERCHANT_CODE = "LAPARQUE001"
IBAN_PREFIX = "TR"


def generate_reference(payment_id: Optional[int] = None) -> str:
    """
    Unique reference code üretir
    Format: PAY-{timestamp}-{random}
    """
    from datetime import datetime
    import secrets
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    # 6 haneli random sayı ekle (unique olması için)
    random_suffix = secrets.randbelow(1000000)
    if payment_id:
        return f"PAY-{payment_id:06d}-{timestamp}-{random_suffix:06d}"
    else:
        return f"PAY-{timestamp}-{random_suffix:06d}"


def generate_iban() -> str:
    """
    Örnek TR IBAN üretir
    Format: TR33 0001 0000 0000 0000 0000 00
    """
    # Gerçek IBAN formatı: TR + 2 kontrol hanesi + 4 banka kodu + 1 rezerv + 16 hesap no
    # Simülasyon için sabit bir IBAN kullanıyoruz
    return "TR33000100000000000000000000"


def create_qr_content(payment: Payment) -> Dict[str, any]:
    """
    Payment bilgilerinden QR içeriğini oluşturur
    
    Args:
        payment: Payment model instance
    
    Returns:
        QR içeriği (dict)
    """
    qr_data = {
        "receiver_name": payment.receiver_name,
        "iban": payment.iban,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "reference": payment.reference,
        "merchant_code": payment.merchant_code
    }
    
    logger.info(f"QR content generated for payment {payment.id}: {payment.reference}")
    return qr_data


def create_qr_json(payment: Payment) -> str:
    """
    Payment bilgilerinden JSON formatında QR içeriği oluşturur
    
    Args:
        payment: Payment model instance
    
    Returns:
        JSON string
    """
    qr_data = create_qr_content(payment)
    return json.dumps(qr_data, ensure_ascii=False)

