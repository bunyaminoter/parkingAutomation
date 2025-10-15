import React, { useRef, useState, useEffect } from "react";
import API from "../api";

export default function CameraCaptureCard({ onCreated }) {
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Kamera toggle
  const toggleCamera = async () => {
    if (active) {
      if (stream) stream.getTracks().forEach((t) => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
      setStream(null);
      setActive(false);
      setError("");
    } else {
      try {
        const newStream = await navigator.mediaDevices.getUserMedia({ video: true });
        setStream(newStream);
        setActive(true);
        setError("");
      } catch (err) {
        console.error(err);
        setError("Kamera erişimi reddedildi veya bulunamadı");
      }
    }
  };

  // 📸 Kamera stream’i ref’e bağla
  useEffect(() => {
    if (active && videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, active]);

  // Fotoğraf çek
  const captureFrame = async () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0);

    canvas.toBlob(async (blob) => {
      setLoading(true);
      setError("");
      try {
        const fd = new FormData();
        fd.append("file", blob, "capture.jpg");

        const res = await fetch(API.base + API.uploadImage, {
          method: "POST",
          body: fd,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Yükleme hatası oluştu");
        }

        onCreated?.();
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }, "image/jpeg");
  };

  return (
    <div className="card">
      <h2>Canlı Kameradan Plaka Tanıma</h2>
      <button onClick={toggleCamera} style={{ marginBottom: "12px" }}>
        {active ? "Kamerayı Kapat" : "Kamerayı Başlat"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {active && (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={{
              width: "100%",
              borderRadius: "12px",
              border: "2px solid #ccc",
            }}
          />
          <div style={{ marginTop: "12px" }}>
            <button onClick={captureFrame} disabled={loading}>
              {loading ? "Yükleniyor..." : "Fotoğraf Çek ve Gönder"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
