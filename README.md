# Parking Automation System

Otomatik plaka tanıma sistemi ile park yönetimi uygulaması.


### Hızlı Başlatma
```bash
  # API bağlantısını başlat
uvicorn backend.main:app
```

```bash
  # Frontendi başlat http://localhost:5173/
npm run dev
cd frontend
```

## 🚀 Özellikler

- **Plaka Tanıma**: Resim ve video dosyalarından otomatik plaka tanıma
- **Manuel Giriş**: Plaka numarası ile manuel park kaydı oluşturma
- **Çıkış İşlemi**: Park kayıtlarını tamamlama
- **Kayıt Yönetimi**: Tüm park kayıtlarını görüntüleme ve yönetme
- **Gerçek Zamanlı**: Anlık güncellemeler ve durum takibi

## 🛠️ Teknolojiler

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM ve veritabanı yönetimi
- **PostgreSQL**: Ana veritabanı
- **Alembic**: Veritabanı migrasyonları
- **OpenCV + Tesseract**: Plaka tanıma

### Frontend
- **React 19**: Modern UI framework
- **Vite**: Hızlı build tool
- **CSS3**: Responsive tasarım

## 📋 Kurulum

### 1. Veritabanı Kurulumu
```bash
# PostgreSQL kurulumu (Windows)
# https://www.postgresql.org/download/windows/

# Veritabanı oluşturma
createdb parkingAutomation
```

### 2. Backend Kurulumu
```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Veritabanı migrasyonlarını çalıştır
alembic upgrade head

# Backend'i başlat
uvicorn backend.main:app
```

### 3. Frontend Kurulumu
```bash
# Frontend dizinine git
cd frontend

# Bağımlılıkları yükle
npm install

# Frontend'i başlat
cd frontend
npm run dev
```

## 🌐 Erişim

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Dokümantasyonu**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## 📊 Veritabanı Yapısı

### parking_records
- `id`: Primary Key
- `plate_number`: Plaka numarası (String(32), Indexed, Not Null)
- `entry_time`: Giriş saati (DateTime, Default: Current Timestamp)
- `exit_time`: Çıkış saati (DateTime, Nullable)
- `fee`: Ücret (Float, Default: 0.0)


## 🔧 API Endpoints

### Park Kayıtları
- `GET /api/parking_records` - Tüm kayıtları listele
- `POST /api/parking_records` - Yeni kayıt oluştur
- `PUT /api/parking_records/{id}/exit` - Çıkış işlemi

### Manuel Giriş
- `POST /api/manual_entry` - Manuel plaka girişi

### Dosya Yükleme
- `POST /api/upload/image` - Resimden plaka tanıma
- `POST /api/upload/video` - Videodan plaka tanıma

### Sistem
- `GET /api/health` - Sistem durumu

## 🚀 Kullanım

1. **Manuel Giriş**: Plaka numarasını girerek park kaydı oluşturun
2. **Resim Yükleme**: Araç resmini yükleyerek otomatik plaka tanıma
3. **Canlı Kamera**: Canlı kamera ile otomatik plaka tanıma
4. **Çıkış İşlemi**: Kayıtlar tablosundan "Çıkış Yap" butonuna tıklayın

## 🔍 Sorun Giderme

### Backend Sorunları
- PostgreSQL servisinin çalıştığından emin olun
- Veritabanı bağlantı bilgilerini kontrol edin (`backend/database.py`)
- Migrasyonları çalıştırın: `alembic upgrade head`

### Frontend Sorunları
- Backend'in çalıştığından emin olun
- CORS ayarlarını kontrol edin
- Browser console'da hata mesajlarını kontrol edin

### Plaka Tanıma Sorunları
- OpenCV ve Tesseract kurulumunu kontrol edin
- Resim/Kamera kalitesinin yeterli olduğundan emin olun
- Plaka numarasının net görünür olduğundan emin olun

## 📝 Notlar

- Sistem sadece plaka numarası ve giriş/çıkış saatlerini tutar
- Tüm işlemler gerçek zamanlı olarak güncellenir
- Veritabanı migrasyonları Alembic ile yönetilir
