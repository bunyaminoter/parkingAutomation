"""
Barrier Service - Bariyer kontrolü ve açma simülasyonu
"""
import logging
from backend.models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


class BarrierService:
    """Bariyer kontrolü ve açma servisi"""
    
    @staticmethod
    async def open_barrier(payment: Payment) -> bool:
        """
        Ödeme tamamlandıysa bariyeri açar
        
        Args:
            payment: Payment model instance
        
        Returns:
            bool: Bariyer açıldıysa True
        
        Raises:
            ValueError: Ödeme tamamlanmamışsa
        """
        if payment.status != PaymentStatus.PAID:
            error_msg = f"Payment {payment.id} is not PAID. Current status: {payment.status.value}"
            logger.warning(error_msg)
            raise ValueError(error_msg)
        
        # Bariyer açma simülasyonu
        logger.info(f"🚧 Opening barrier for payment {payment.id} (Reference: {payment.reference})")
        logger.info(f"   Amount: {payment.amount} {payment.currency}")
        logger.info(f"   ✅ Barrier opened successfully")
        
        return True
    
    @staticmethod
    def can_open_barrier(payment: Payment) -> bool:
        """
        Bariyerin açılıp açılamayacağını kontrol eder
        
        Args:
            payment: Payment model instance
        
        Returns:
            bool: Bariyer açılabilirse True
        """
        return payment.status == PaymentStatus.PAID


