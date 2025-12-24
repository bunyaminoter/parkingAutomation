"""
Authentication routes - Login, logout, session management
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import secrets

from backend.database import SessionLocal
from backend import models
from backend.utils.session_manager import (
    create_session_token,
    get_session_user,
    delete_session,
    SESSION_COOKIE_NAME,
)
from backend.services.email_service import send_password_reset_email
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




@router.post("/login")
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Admin girişi - cookie ve session token oluşturur"""
    # Email doğrulama
    if "@" not in email or "." not in email.split("@")[1]:
        raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi giriniz")
    
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    # Kullanıcıyı kontrol et
    user = db.query(models.User).filter(
        models.User.email == email,
        models.User.password == hashed_password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz e-posta veya şifre")

    if user.is_super_admin == 1:
        raise HTTPException(
            status_code=403,
            detail="Üst Admin yetkisine sahipsiniz. Lütfen Üst Admin Giriş sayfasını kullanın."
        )

    # Session token oluştur
    session_token = create_session_token(user.id, user.email, remember_me)
    
    # Cookie ayarları
    from backend.utils.session_manager import SESSION_DURATION_DAYS
    if remember_me:
        max_age = SESSION_DURATION_DAYS * 24 * 60 * 60
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age,
            httponly=True,
            samesite="lax",
            secure=False  # HTTPS kullanıyorsanız True yapın
        )
    else:
        # Session cookie - tarayıcı kapanınca silinir
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False
        )
    
    return {
        "success": True,
        "message": "Giriş başarılı",
        "user": {
            "id": user.id,
            "email": user.email
        }
    }


@router.post("/super_admin/login")
def super_admin_login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Üst admin girişi - sadece is_super_admin=1 olan kullanıcılar giriş yapabilir"""
    # Email doğrulama
    if "@" not in email or "." not in email.split("@")[1]:
        raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi giriniz")
    
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    # Kullanıcıyı kontrol et
    user = db.query(models.User).filter(
        models.User.email == email,
        models.User.password == hashed_password,
        models.User.is_super_admin == 1
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz e-posta veya şifre veya üst admin yetkisi yok")
    
    # Session token oluştur (remember_me=False, üst admin için)
    session_token = create_session_token(user.id, user.email, remember_me=False)
    
    # Cookie ayarları
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    return {
        "success": True,
        "message": "Üst admin girişi başarılı",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_super_admin": user.is_super_admin
        }
    }


@router.get("/check_session")
def check_session(request: Request, db: Session = Depends(get_db)):
    """Mevcut session'ı kontrol eder"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Session bulunamadı")
    
    session = get_session_user(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session geçersiz veya süresi dolmuş")
    
    # Kullanıcıyı veritabanından al
    user = db.query(models.User).filter(models.User.id == session["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_super_admin": user.is_super_admin
        },
        "remember_me": session.get("remember_me", False)
    }


@router.post("/logout")
def logout(response: Response, request: Request):
    """Çıkış yapar ve session'ı siler"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)
    
    # Cookie'yi sil
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    
    return {"success": True, "message": "Çıkış başarılı"}


@router.get("/user_login")
def user_login():
    """Kullanıcı girişi (şifre gerektirmez)"""
    return {
        "success": True,
        "message": "Kullanıcı girişi başarılı",
        "user_type": "user"
    }


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(
    request_data: ForgotPasswordRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Şifre sıfırlama token'ı oluştur ve e-posta gönder"""
    email = request_data.email.strip()
    
    # Email doğrulama
    if "@" not in email or "." not in email.split("@")[1]:
        raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi giriniz")
    
    # Kullanıcıyı bul
    user = db.query(models.User).filter(models.User.email == email).first()
    
    # Güvenlik için: Kullanıcı yoksa bile başarılı mesajı döndür
    if not user:
        return {
            "success": True,
            "message": "Eğer bu e-posta adresi kayıtlıysa, şifre sıfırlama bağlantısı gönderildi."
        }
    
    # Mevcut token'ları iptal et (aynı email için)
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.email == email,
        models.PasswordResetToken.used == 0
    ).update({"used": 1})
    
    # Yeni token oluştur
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 saat geçerli
    
    reset_token = models.PasswordResetToken(
        email=email,
        token=token,
        expires_at=expires_at,
        used=0
    )
    db.add(reset_token)
    db.commit()
    
    # Development modu kontrolü (email göndermeden önce)
    import os
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    dev_mode_env = os.getenv("DEV_MODE", "").lower() == "true"
    dev_mode = dev_mode_env or (not smtp_user or not smtp_password)
    
    # E-posta gönder
    email_sent = await send_password_reset_email(email, token)
    
    if not email_sent:
        if dev_mode:
            # Development modunda token'ı response'da döndür
            reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/reset-password?token={token}"
            logger.info(f"✅ Development modu: Token oluşturuldu ve response'da döndürülüyor")
            return {
                "success": True,
                "dev_mode": True,
                "message": "Development modunda çalışıyorsunuz. Email gönderilmedi, token aşağıda görüntüleniyor.",
                "reset_link": reset_link,
                "token": token
            }
        else:
            # Production modunda gerçekten email gönderilemedi
            db.delete(reset_token)
            db.commit()
            error_detail = (
                "E-posta gönderilemedi. Lütfen SMTP ayarlarını kontrol edin veya "
                "sistem yöneticisi ile iletişime geçin. "
                "Backend loglarını kontrol edin."
            )
            raise HTTPException(
                status_code=500,
                detail=error_detail
            )
    
    return {
        "success": True,
        "dev_mode": False,
        "message": "Eğer bu e-posta adresi kayıtlıysa, şifre sıfırlama bağlantısı gönderildi."
    }


@router.post("/reset-password")
def reset_password(
    request_data: ResetPasswordRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Token ile şifreyi sıfırla"""
    token = request_data.token.strip()
    new_password = request_data.new_password.strip()
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalıdır")
    
    # Token'ı bul ve kontrol et
    reset_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token,
        models.PasswordResetToken.used == 0
    ).first()
    
    if not reset_token:
        raise HTTPException(status_code=400, detail="Geçersiz veya kullanılmış token")
    
    # Token süresi dolmuş mu kontrol et
    if datetime.utcnow() > reset_token.expires_at:
        reset_token.used = 1
        db.commit()
        raise HTTPException(status_code=400, detail="Token süresi dolmuş")
    
    # Kullanıcıyı bul
    user = db.query(models.User).filter(models.User.email == reset_token.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Şifreyi güncelle
    hashed_password = hashlib.md5(new_password.encode()).hexdigest()
    user.password = hashed_password
    
    # Token'ı kullanıldı olarak işaretle
    reset_token.used = 1
    
    db.commit()
    
    return {
        "success": True,
        "message": "Şifre başarıyla güncellendi"
    }


@router.get("/verify-reset-token/{token}")
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """Token'ın geçerli olup olmadığını kontrol et"""
    reset_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token,
        models.PasswordResetToken.used == 0
    ).first()
    
    if not reset_token:
        return {"valid": False, "message": "Geçersiz token"}
    
    if datetime.utcnow() > reset_token.expires_at:
        return {"valid": False, "message": "Token süresi dolmuş"}
    
    return {"valid": True, "email": reset_token.email}

