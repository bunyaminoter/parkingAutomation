import cv2
from backend.services.plate_recognition import recognize_plate_from_bytes
import time

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera açılamadı!")
    exit()

print("Kamera başlatıldı. 'q' ile çıkabilirsin.")

last_detect_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    #  saniyede bir kontrol et (performans için)
    if time.time() - last_detect_time > 1:
        # Görüntüyü belleğe kaydet
        _, buffer = cv2.imencode(".jpg", frame)
        content = buffer.tobytes()

        # Plaka tanıma
        plate, conf = recognize_plate_from_bytes(content, lang_list=["tr","en"], gpu=False)
        if plate:
            print(f"Plaka bulundu: {plate} (güven: {conf:.2f})")

        last_detect_time = time.time()

    cv2.imshow("Canlı Kamera - Plaka Tanıma", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
