"""
User routes - User CRUD operations, password management
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import hashlib

from backend.database import SessionLocal
from backend import models
from backend.utils.session_manager import get_session_user, SESSION_COOKIE_NAME


class UpdateMyInfoRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

router = APIRouter(prefix="/api", tags=["users"])


class UserUpdate(BaseModel):
    email: Optional[str] = None
    is_super_admin: Optional[int] = None


class PasswordUpdate(BaseModel):
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    is_super_admin: int = 0


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_super_admin(request: Request, db: Session = Depends(get_db)):
    """Üst admin kontrolü yapar"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Session bulunamadı")
    
    session = get_session_user(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session geçersiz veya süresi dolmuş")
    
    user = db.query(models.User).filter(models.User.id == session["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    
    if user.is_super_admin != 1:
        raise HTTPException(status_code=403, detail="Üst admin yetkisi gerekli")
    
    return user


def require_auth(request: Request, db: Session = Depends(get_db)):
    """Giriş yapmış kullanıcı kontrolü yapar"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Session bulunamadı")
    
    session = get_session_user(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session geçersiz veya süresi dolmuş")
    
    user = db.query(models.User).filter(models.User.id == session["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    
    return user


@router.get("/users")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_super_admin)
):
    """Tüm kullanıcıları listele (sadece üst admin)"""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "is_super_admin": u.is_super_admin,
            "created_at": u.created_at
        }
        for u in users
    ]


@router.post("/users")
def create_user(
    request: Request,
    user_data: UserCreate = Body(...),
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_super_admin)
):
    """Yeni kullanıcı oluştur (sadece üst admin)"""
    # Email doğrulama
    if "@" not in user_data.email or "." not in user_data.email.split("@")[1]:
        raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi giriniz")
    
    # Email kontrolü
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kullanılıyor")
    
    # Şifreyi hash'le
    hashed_password = hashlib.md5(user_data.password.encode()).hexdigest()
    
    # Yeni kullanıcı oluştur
    new_user = models.User(
        email=user_data.email,
        password=hashed_password,
        is_super_admin=1 if user_data.is_super_admin else 0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "is_super_admin": new_user.is_super_admin,
        "created_at": new_user.created_at
    }


@router.put("/users/{user_id}")
def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate = Body(...),
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_super_admin)
):
    """Kullanıcı bilgilerini güncelle (sadece üst admin)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Email güncelleme
    if user_data.email is not None and user_data.email.strip():
        # Email doğrulama
        if "@" not in user_data.email or "." not in user_data.email.split("@")[1]:
            raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi giriniz")
        
        # Email kontrolü (kendisi hariç)
        existing_user = db.query(models.User).filter(
            models.User.email == user_data.email.strip(),
            models.User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kullanılıyor")
        user.email = user_data.email.strip()
    
    # Üst admin durumu güncelleme
    if user_data.is_super_admin is not None:
        user.is_super_admin = 1 if user_data.is_super_admin else 0
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "is_super_admin": user.is_super_admin,
        "created_at": user.created_at
    }


@router.put("/users/{user_id}/password")
def change_user_password(
    request: Request,
    user_id: int,
    password_data: PasswordUpdate = Body(...),
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_super_admin)
):
    """Kullanıcı şifresini değiştir (sadece üst admin)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Şifreyi hash'le
    hashed_password = hashlib.md5(password_data.password.encode()).hexdigest()
    user.password = hashed_password
    
    db.commit()
    
    return {"success": True, "message": "Şifre güncellendi"}


@router.delete("/users/{user_id}")
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_super_admin)
):
    """Kullanıcıyı sil (sadece üst admin)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Kendini silmeyi engelle
    if user.id == _current_user.id:
        raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz")
    
    db.delete(user)
    db.commit()
    
    return {"success": True, "message": "Kullanıcı silindi"}


@router.put("/users/me/update")
def update_my_info(
    request: Request,
    update_data: UpdateMyInfoRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth)
):
    """Kendi kullanıcı bilgilerini güncelle (email ve şifre)"""
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Email güncelleme
    if update_data.email is not None and update_data.email.strip():
        email = update_data.email.strip()
        
        # Email doğrulama
        if "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi giriniz")
        
        # Email kontrolü (kendisi hariç)
        existing_user = db.query(models.User).filter(
            models.User.email == email,
            models.User.id != user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kullanılıyor")
        
        user.email = email
    
    # Şifre güncelleme
    if update_data.password is not None and update_data.password.strip():
        if len(update_data.password.strip()) < 6:
            raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalıdır")
        
        hashed_password = hashlib.md5(update_data.password.strip().encode()).hexdigest()
        user.password = hashed_password
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "Bilgileriniz güncellendi",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_super_admin": user.is_super_admin
        }
    }

