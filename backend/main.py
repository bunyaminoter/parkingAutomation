"""
Parking Automation API - Main application file
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import ensure_schema
from backend.routes import (
    auth_routes,
    parking_routes,
    user_routes,
    user_page_routes,
    websocket_routes,
    health_routes,
)

# Veritabanı şemasını kontrol et
ensure_schema()

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

# --------------------------------------------------
# 🔹 Frontend dosyalarını sun (React build sonrası)
# --------------------------------------------------
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/", response_class=HTMLResponse)
def root_index():
    """Ana sayfa - Frontend'e yönlendir"""
    return "<html><head><meta http-equiv='refresh' content='0; url=/frontend/index.html' /></head><body></body></html>"
