#!/usr/bin/env python3
"""
API test scripti - Backend'in çalışıp çalışmadığını test eder
"""
import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_health():
    """Health check endpoint'ini test et"""
    try:
        response = requests.get(f"{API_BASE}/api/health")
        if response.status_code == 200:
            print("✅ Health check: OK")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_manual_entry():
    """Manuel giriş endpoint'ini test et"""
    try:
        data = {"plate_number": "TEST123"}
        response = requests.post(f"{API_BASE}/api/manual_entry", data=data)
        if response.status_code == 200:
            print("✅ Manual entry: OK")
            result = response.json()
            print(f"   Created record ID: {result['id']}")
            return result['id']
        else:
            print(f"❌ Manual entry failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Manual entry error: {e}")
        return None

def test_get_records():
    """Kayıtları listele endpoint'ini test et"""
    try:
        response = requests.get(f"{API_BASE}/api/parking_records")
        if response.status_code == 200:
            print("✅ Get records: OK")
            records = response.json()
            print(f"   Found {len(records)} records")
            return records
        else:
            print(f"❌ Get records failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Get records error: {e}")
        return None

def test_complete_record(record_id):
    """Çıkış işlemi endpoint'ini test et"""
    try:
        data = {"fee": 0}
        response = requests.put(f"{API_BASE}/api/parking_records/{record_id}/exit", json=data)
        if response.status_code == 200:
            print("✅ Complete record: OK")
            result = response.json()
            print(f"   Exit time: {result['exit_time']}")
            return True
        else:
            print(f"❌ Complete record failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Complete record error: {e}")
        return False

def main():
    print("🧪 API Test Başlatılıyor...")
    print("=" * 50)
    
    # Health check
    if not test_health():
        print("\n❌ Backend çalışmıyor! Lütfen backend'i başlatın.")
        sys.exit(1)
    
    print()
    
    # Manuel giriş testi
    record_id = test_manual_entry()
    if not record_id:
        print("\n❌ Manuel giriş testi başarısız!")
        sys.exit(1)
    
    print()
    
    # Kayıtları listele testi
    records = test_get_records()
    if records is None:
        print("\n❌ Kayıtları listele testi başarısız!")
        sys.exit(1)
    
    print()
    
    # Çıkış işlemi testi
    if not test_complete_record(record_id):
        print("\n❌ Çıkış işlemi testi başarısız!")
        sys.exit(1)
    
    print()
    print("🎉 Tüm testler başarılı!")
    print("✅ Backend API düzgün çalışıyor.")

if __name__ == "__main__":
    main()

