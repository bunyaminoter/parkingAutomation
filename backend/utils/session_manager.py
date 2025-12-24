"""
Session management utilities
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets

# Session yönetimi için in-memory storage (production'da Redis kullanılabilir)
active_sessions: Dict[str, dict] = {}
SESSION_COOKIE_NAME = "parking_session_token"
SESSION_DURATION_DAYS = 7  # "Beni hatırla" için
SESSION_DURATION_HOURS = 24  # Normal session için


def create_session_token(user_id: int, email: str, remember_me: bool = False) -> str:
    """Yeni session token oluşturur"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + (
        timedelta(days=SESSION_DURATION_DAYS) if remember_me 
        else timedelta(hours=SESSION_DURATION_HOURS)
    )
    active_sessions[token] = {
        "user_id": user_id,
        "email": email,
        "expires_at": expires_at,
        "remember_me": remember_me
    }
    return token


def get_session_user(token: str) -> Optional[dict]:
    """Session token'dan kullanıcı bilgisini alır"""
    if token not in active_sessions:
        return None
    
    session = active_sessions[token]
    if datetime.utcnow() > session["expires_at"]:
        # Süresi dolmuş session'ı temizle
        del active_sessions[token]
        return None
    
    return session


def delete_session(token: str):
    """Session'ı siler"""
    if token in active_sessions:
        del active_sessions[token]

