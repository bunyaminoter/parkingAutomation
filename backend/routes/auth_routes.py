"""
Authentication routes - Login, logout, session management
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy.orm import Session
import hashlib

from backend.database import SessionLocal
from backend import models
from backend.utils.session_manager import (
    create_session_token,
    get_session_user,
    delete_session,
    SESSION_COOKIE_NAME,
)

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
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Admin girişi - cookie ve session token oluşturur"""
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    # Kullanıcıyı kontrol et
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.password == hashed_password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")
    
    # Session token oluştur
    session_token = create_session_token(user.id, user.username, remember_me)
    
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
            "username": user.username
        }
    }


@router.post("/super_admin/login")
def super_admin_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Üst admin girişi - sadece is_super_admin=1 olan kullanıcılar giriş yapabilir"""
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    # Kullanıcıyı kontrol et
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.password == hashed_password,
        models.User.is_super_admin == 1
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre veya üst admin yetkisi yok")
    
    # Session token oluştur (remember_me=False, üst admin için)
    session_token = create_session_token(user.id, user.username, remember_me=False)
    
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
            "username": user.username,
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
            "username": user.username,
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

