import React, { useEffect, useRef, useState } from "react";
import API from "../api";

const AUTO_CAPTURE_INTERVAL = 3000; // ms

export default function CameraCaptureCard({ onCreated }) {
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [autoProcessing, setAutoProcessing] = useState(false);
  const [autoDetect, setAutoDetect] = useState(true);
  const [error, setError] = useState("");
  const sendingRef = useRef(false);

  const toggleCamera = async () => {
    if (active) {
      if (stream) stream.getTracks().forEach((t) => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
      setStream(null);
      setActive(false);
      setAutoProcessing(false);
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

  useEffect(() => {
    if (active && videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, active]);

  useEffect(() => {
    if (!active || !autoDetect) return undefined;
    const interval = setInterval(() => {
      if (!sendingRef.current) {
        captureFrame({ auto: true });
      }
    }, AUTO_CAPTURE_INTERVAL);
    return () => clearInterval(interval);
  }, [active, autoDetect]);

  const captureFrame = async ({ auto = false } = {}) => {
    if (!videoRef.current) return;
    try {
      const blob = await grabFrameBlob();
      await sendFrame(blob, auto);
    } catch (err) {
      setError(err.message);
    }
  };

  const grabFrameBlob = () =>
    new Promise((resolve, reject) => {
      if (!videoRef.current) {
        reject(new Error("Kamera hazır değil"));
        return;
      }
      const canvas = document.createElement("canvas");
      canvas.width = videoRef.current.videoWidth || 1280;
      canvas.height = videoRef.current.videoHeight || 720;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(videoRef.current, 0, 0);
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Görüntü yakalanamadı"));
            return;
          }
          resolve(blob);
        },
        "image/jpeg",
        0.92
      );
    });

  const sendFrame = async (blob, auto = false) => {
    const fd = new FormData();
    fd.append("file", blob, auto ? "auto_capture.jpg" : "capture.jpg");
    sendingRef.current = true;
    setError("");
    if (auto) {
      setAutoProcessing(true);
    } else {
      setLoading(true);
    }
    try {
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
      sendingRef.current = false;
      setLoading(false);
      setAutoProcessing(false);
    }
  };

  return (
    <div className="card">
      <h2>Canlı Kameradan Plaka Tanıma</h2>
      <button onClick={toggleCamera} style={{ marginBottom: "12px" }}>
        {active ? "Kamerayı Kapat" : "Kamerayı Başlat"}
      </button>

      {active && (
        <div style={{ marginBottom: "12px" }}>
          <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input
              type="checkbox"
              checked={autoDetect}
              onChange={(e) => setAutoDetect(e.target.checked)}
            />
            Otomatik plaka algılama
          </label>
          {autoProcessing && (
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Otomatik algılama çalışıyor...
            </p>
          )}
        </div>
      )}

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
            <button onClick={() => captureFrame()} disabled={loading}>
              {loading ? "Yükleniyor..." : "Fotoğraf Çek ve Gönder"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
