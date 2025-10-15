# backend/services/plate_recognition.py
import cv2
import numpy as np
import easyocr
import re
from typing import Optional, Tuple
from threading import Lock

# reader'ı bir kez başlatıp yeniden kullanmak için cache ve lock
_reader = None
_reader_lock = Lock()

def _get_reader(lang_list=None, gpu=False):
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                if lang_list is None:
                    lang_list = ["en"]
                _reader = easyocr.Reader(lang_list, gpu=False)
    return _reader

# Görüntüyü OpenCV formatına decode eden yardımcı
def _bytes_to_bgr_image(content: bytes):
    arr = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img

# Jupyter'deki 'find_plate_candidates' mantığı — ROI döndürüyor
def _find_plate_candidates(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 100, 200)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.02*cv2.arcLength(cnt, True), True)
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = w / float(h) if h>0 else 0
        area = cv2.contourArea(cnt)
        if 2 < aspect_ratio < 6 and 1000 < area < 20000:   # eşikleri ihtiyaca göre ayarla
            roi = img_bgr[y:y+h, x:x+w]
            if roi.size > 0:
                candidates.append(roi)
    return candidates

# Jupyter'deki fix_plate_text fonksiyonunun daha genel hali
def _fix_plate_text(text: str) -> Optional[str]:
    if not text:
        return None
    t = re.sub(r'[^A-Z0-9]', '', text.upper())
    # Basit karakter düzeltmeleri
    t_basic = t.replace("I","1").replace("L","1").replace("O","0")
    # Türkiye plakası için kabaca kontrol: 6-8 uzunluk
    if not (4 <= len(t_basic) <= 8):
        return None
    # Daha ileri kurallar istersen buraya ekle
    # dönüş olarak normalize edilmiş string döndür
    return t_basic

# Ana fonksiyon: bytes içerikten plaka döndürür (ve opsiyonel confidence)
def recognize_plate_from_bytes(content: bytes, lang_list=None, gpu=False) -> Tuple[Optional[str], float]:
    """
    content: image bytes (dosya.read() şeklinde)
    returns: (plate_number_or_None, confidence 0..1)
    """
    try:
        img = _bytes_to_bgr_image(content)
        if img is None:
            return None, 0.0

        candidates = _find_plate_candidates(img)
        # fallback: tüm resim üzerinde OCR dene
        regions = candidates if candidates else [img]

        reader = _get_reader(lang_list=lang_list or ["en","tr"], gpu=gpu)

        ocr_results = []
        for roi in regions:
            # optionally preprocess roi: resize, thresholding vs.
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            # ölçekleme: küçükse büyüt
            h, w = roi_gray.shape[:2]
            scale = 1.0
            if w < 200:
                scale = 2.0
            roi_proc = cv2.resize(roi_gray, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_LINEAR)
            # OCR
            res = reader.readtext(roi_proc)
            for box, text, conf in res:
                # conf EasyOCR'de 0..1 aralığında olabilir veya 0..100, normalize et
                conf_norm = conf if conf <= 1 else conf/100.0
                ocr_results.append((text, conf_norm))

        if not ocr_results:
            return None, 0.0

        # en iyi sonucu seç
        ocr_results.sort(key=lambda x: x[1], reverse=True)
        for text, conf in ocr_results:
            plate_candidate = _fix_plate_text(text)
            if plate_candidate:
                return plate_candidate, conf

        return None, 0.0

    except Exception as e:
        # hata loglamak iyi olur (logger)
        return None, 0.0
