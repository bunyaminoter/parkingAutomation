"""
Email service for sending password reset emails
"""
import os
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# SMTP ayarları (environment variables'dan alınır)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
# SMTP_PASSWORD'daki boşlukları temizle (Gmail App Password'ları bazen boşluklu gelir)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip().replace(" ", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER).strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Development modu kontrolü
# DEV_MODE=true ise veya SMTP ayarları yoksa development modu aktif
DEV_MODE_ENV = os.getenv("DEV_MODE", "").lower()
DEV_MODE = DEV_MODE_ENV == "true" or (DEV_MODE_ENV == "" and (not SMTP_USER or not SMTP_PASSWORD))

# SMTP ayarları logla
if DEV_MODE:
    logger.info("🔧 Development modu aktif")
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.info("   → SMTP ayarları yapılandırılmamış, bu yüzden development modu aktif")
    else:
        logger.info("   → DEV_MODE=true olduğu için development modu aktif")
else:
    logger.info(f"📧 Production modu - Email gönderimi aktif")
    logger.info(f"   SMTP_HOST: {SMTP_HOST}")
    logger.info(f"   SMTP_PORT: {SMTP_PORT}")
    logger.info(f"   SMTP_USER: {SMTP_USER[:3]}***@{SMTP_USER.split('@')[1] if '@' in SMTP_USER else '***'}")
    logger.info(f"   SMTP_PASSWORD: {'SET' if SMTP_PASSWORD else 'NOT SET'}")


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Şifre sıfırlama e-postası gönderir
    
    Args:
        to_email: Alıcı e-posta adresi
        reset_token: Şifre sıfırlama token'ı
    
    Returns:
        bool: E-posta başarıyla gönderildiyse True
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    
    # Development modu: Email göndermek yerine console'a yazdır
    if DEV_MODE:
        logger.info("=" * 80)
        logger.info("🔧 DEV MODE: Email gönderilmeyecek, token console'a yazdırılıyor")
        logger.info(f"📧 Alıcı: {to_email}")
        logger.info(f"🔗 Şifre Sıfırlama Linki: {reset_link}")
        logger.info(f"🔑 Token: {reset_token}")
        logger.info("=" * 80)
        return True
    
    # SMTP credentials kontrolü (artık DEV_MODE kontrolü yukarıda yapılıyor)
    # Buraya gelirse zaten DEV_MODE false demektir, o yüzden credentials olmalı
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error(
            f"SMTP credentials not configured. "
            f"SMTP_USER: {'SET' if SMTP_USER else 'NOT SET'}, "
            f"SMTP_PASSWORD: {'SET' if SMTP_PASSWORD else 'NOT SET'}"
        )
        logger.error(
            "Lütfen environment variables'ları ayarlayın: "
            "SMTP_USER, SMTP_PASSWORD"
        )
        logger.info(
            "💡 İpucu: Development modunda test etmek için DEV_MODE=true ayarlayın "
            "veya SMTP ayarlarını yapılandırın."
        )
        return False
    
    try:
        # E-posta içeriği
        message = MIMEMultipart("alternative")
        message["Subject"] = "Şifre Sıfırlama - Parking Automation"
        message["From"] = SMTP_FROM_EMAIL
        message["To"] = to_email
        
        # HTML içerik
        html_content = f"""
        <html>
          <body>
            <h2>Şifre Sıfırlama İsteği</h2>
            <p>Merhaba,</p>
            <p>Parking Automation sisteminde şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:</p>
            <p><a href="{reset_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Şifremi Sıfırla</a></p>
            <p>Veya bu bağlantıyı tarayıcınıza kopyalayın:</p>
            <p>{reset_link}</p>
            <p>Bu bağlantı 1 saat süreyle geçerlidir.</p>
            <p>Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.</p>
            <br>
            <p>Saygılarımızla,<br>Parking Automation Ekibi</p>
          </body>
        </html>
        """
        
        # Plain text içerik
        text_content = f"""
        Şifre Sıfırlama İsteği
        
        Merhaba,
        
        Parking Automation sisteminde şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
        
        {reset_link}
        
        Bu bağlantı 1 saat süreyle geçerlidir.
        
        Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.
        
        Saygılarımızla,
        Parking Automation Ekibi
        """
        
        # İçerikleri ekle
        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        
        message.attach(part1)
        message.attach(part2)
        
        # E-postayı gönder
        logger.info(f"Attempting to send password reset email to {to_email} via {SMTP_HOST}:{SMTP_PORT}")
        logger.info(f"Using username: {SMTP_USER}")
        logger.info(f"Password length: {len(SMTP_PASSWORD)} characters")
        
        # Gmail için port 587'de STARTTLS, port 465'te SSL/TLS kullanılır
        # aiosmtplib.send() fonksiyonu otomatik olarak doğru yöntemi seçer
        # Port 587 için use_tls=False (STARTTLS kullanılacak)
        # Port 465 için use_tls=True (SSL/TLS kullanılacak)
        use_tls = (SMTP_PORT == 465)
        
        logger.info(f"Using {'SSL/TLS' if use_tls else 'STARTTLS'} connection")
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=use_tls,  # Port 465 için True, port 587 için False
            timeout=30,  # Timeout'u artırdık
        )
        
        logger.info(f"✅ Password reset email sent successfully to {to_email}")
        return True
        
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP Authentication failed: {str(e)}")
        logger.error("Lütfen SMTP_USER ve SMTP_PASSWORD'ın doğru olduğundan emin olun")
        return False
    except aiosmtplib.SMTPException as e:
        logger.error(f"❌ SMTP Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send password reset email to {to_email}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

