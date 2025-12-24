"""
Parking Automation API - Main application file
"""
import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# .env dosyasını yükle (eğer varsa)
try:
    from dotenv import load_dotenv
    # Proje kök dizininde .env dosyasını yükle
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logging.getLogger(__name__).info(f"✅ .env dosyası yüklendi: {env_path}")
    else:
        logging.getLogger(__name__).warning(f"⚠️  .env dosyası bulunamadı: {env_path}")
except ImportError:
    logging.getLogger(__name__).warning("⚠️  python-dotenv yüklü değil. .env dosyası yüklenemiyor.")

from backend.database import ensure_schema

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)
from backend.routes import (
    auth_routes,
    parking_routes,
    user_routes,
    user_page_routes,
    websocket_routes,
    health_routes,
    payment_routes,
)

# Veritabanı şemasını kontrol et
ensure_schema()

# SMTP ayarlarını kontrol et ve logla
smtp_user = os.getenv("SMTP_USER", "")
smtp_password = os.getenv("SMTP_PASSWORD", "")
dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

if dev_mode:
    logger.info("🔧 Development modu aktif - Email gönderilmeyecek, token console'da görüntülenecek")
elif not smtp_user or not smtp_password:
    logger.warning(
        "⚠️  SMTP ayarları yapılandırılmamış! "
        "Şifre sıfırlama özelliği çalışmayacak. "
        "Lütfen SMTP_USER ve SMTP_PASSWORD environment variables'larını ayarlayın."
    )
else:
    logger.info(f"✅ SMTP ayarları yapılandırıldı: {smtp_user} @ {os.getenv('SMTP_HOST', 'smtp.gmail.com')}")

# --------------------------------------------------
# 🔹 Uygulama nesnesi oluştur
# --------------------------------------------------
app = FastAPI(title="Parking Automation API", version="1.0.0")

# --------------------------------------------------
# 🔹 CORS ayarları (React erişimi için)
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# 🔹 Route'ları include et
# --------------------------------------------------
app.include_router(health_routes.router)
app.include_router(auth_routes.router)
app.include_router(parking_routes.router)
app.include_router(user_routes.router)
app.include_router(user_page_routes.router)
app.include_router(websocket_routes.router)
app.include_router(payment_routes.router)

# --------------------------------------------------
# 🔹 Frontend dosyalarını sun (React build sonrası)
# --------------------------------------------------
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/", response_class=HTMLResponse)
def root_index():
    """Ana sayfa - Frontend'e yönlendir"""
    return "<html><head><meta http-equiv='refresh' content='0; url=/frontend/index.html' /></head><body></body></html>"
