import React, { useEffect, useRef, useState, useCallback } from "react";
import API from "../api";

const AUTO_CAPTURE_INTERVAL = 3000;

export default function CameraCaptureCard({ onCreated }) {
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [autoProcessing, setAutoProcessing] = useState(false);
  const [autoDetect, setAutoDetect] = useState(true);
  const [error, setError] = useState("");
  const sendingRef = useRef(false);
  const onCreatedRef = useRef(onCreated);

  // onCreated callback'ini ref'te tut
  useEffect(() => {
    onCreatedRef.current = onCreated;
  }, [onCreated]);

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
        const newStream = await navigator.mediaDevices.getUserMedia({ 
          video: { 
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "environment"
          } 
        });
        setStream(newStream);
        setActive(true);
        setError("");
      } catch (err) {
        setError("Kamera erişimi reddedildi veya bulunamadı. Lütfen tarayıcı izinlerini kontrol edin.");
      }
    }
  };

  useEffect(() => {
    if (active && videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, active]);

  const grabFrameBlob = useCallback(() => {
    return new Promise((resolve, reject) => {
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
  }, []);

  const sendFrame = useCallback(async (blob, auto = false) => {
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
      onCreatedRef.current?.();
    } catch (err) {
      setError(err.message);
    } finally {
      sendingRef.current = false;
      setLoading(false);
      setAutoProcessing(false);
    }
  }, []);

  const captureFrame = useCallback(async ({ auto = false } = {}) => {
    if (!videoRef.current) return;
    try {
      const blob = await grabFrameBlob();
      await sendFrame(blob, auto);
    } catch (err) {
      setError(err.message);
    }
  }, [grabFrameBlob, sendFrame]);

  useEffect(() => {
    if (!active || !autoDetect) return undefined;
    const interval = setInterval(() => {
      if (!sendingRef.current && videoRef.current) {
        captureFrame({ auto: true });
      }
    }, AUTO_CAPTURE_INTERVAL);
    return () => clearInterval(interval);
  }, [active, autoDetect, captureFrame]);

  return (
    <div className="card">
      <h2>Canlı Kameradan Plaka Tanıma</h2>
      <button 
        onClick={toggleCamera} 
        className="camera-toggle-btn"
        style={{ marginBottom: "16px" }}
      >
        {active ? "Kamerayı Kapat" : "Kamerayı Başlat"}
      </button>

      {active && (
        <div className="auto-detect-toggle">
          <label>
            <input
              type="checkbox"
              checked={autoDetect}
              onChange={(e) => setAutoDetect(e.target.checked)}
            />
            <span>Otomatik plaka algılama (3 saniyede bir)</span>
          </label>
          {autoProcessing && (
            <span className="muted" style={{ fontSize: "0.75rem" }}>
              <span className="loading-spinner" style={{ marginRight: "4px" }}></span>
              Algılanıyor...
            </span>
          )}
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {active && (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="camera-video"
          />
          <div style={{ marginTop: "12px" }}>
            <button 
              onClick={() => captureFrame()} 
              disabled={loading}
              className="capture-btn"
            >
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Yükleniyor...
                </>
              ) : (
                "Fotoğraf Çek ve Gönder"
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
