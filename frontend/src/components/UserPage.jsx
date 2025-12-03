import React, { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import { fetchJSON } from "../utils";
import "./UserPage.css";

const AUTO_CAPTURE_INTERVAL = 3000; // ms

export default function UserPage() {
  const videoRef = useRef(null);
  const sendingRef = useRef(false);
  const [stream, setStream] = useState(null);
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [autoDetect, setAutoDetect] = useState(false);
  const [autoProcessing, setAutoProcessing] = useState(false);
  const [error, setError] = useState("");
  const [recognizedPlate, setRecognizedPlate] = useState("");
  const [confidence, setConfidence] = useState(0);
  const [history, setHistory] = useState([]);
  const [sessionEntries, setSessionEntries] = useState([]);
  const navigate = useNavigate();

  // Kamera toggle
  const toggleCamera = async () => {
    if (active) {
      if (stream) stream.getTracks().forEach((t) => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
      setStream(null);
      setActive(false);
      setAutoDetect(false);
      setAutoProcessing(false);
      setError("");
      setRecognizedPlate("");
      setConfidence(0);
      setHistory([]);
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

  // 📸 Kamera stream'i ref'e bağla
  useEffect(() => {
    if (active && videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, active]);

  // Otomatik algılama döngüsü
  useEffect(() => {
    if (!active || !autoDetect) return undefined;
    const interval = setInterval(() => {
      if (!sendingRef.current) {
        captureAndRecognize(true);
      }
    }, AUTO_CAPTURE_INTERVAL);
    return () => clearInterval(interval);
  }, [active, autoDetect]);

  const fetchHistory = async (plate) => {
    try {
      const data = await fetchJSON(
        API.base + API.getRecordsByPlate(plate)
      );
      setHistory(data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const registerEntry = async (plate, confValue) => {
    try {
      const fd = new FormData();
      fd.append("plate_number", plate);
      if (typeof confValue === "number") {
        fd.append("confidence", String(confValue));
      }
      // Admin tarafındaki manuel_entry endpoint'ini kullanarak giriş/çıkış kaydı oluştur
      await fetch(API.base + API.manualEntry, {
        method: "POST",
        body: fd,
      });
      // Oturum içi "giriş yapan araçlar" listesine ekle
      setSessionEntries((prev) => [
        { plate_number: plate, time: new Date().toISOString() },
        ...prev,
      ]);
    } catch (e) {
      console.error(e);
    }
  };

  // Fotoğraf çek ve plaka tanı
  const captureAndRecognize = async (auto = false) => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 1280;
    canvas.height = videoRef.current.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0);

    canvas.toBlob(
      async (blob) => {
        if (!blob) return;
        sendingRef.current = true;
        if (auto) {
          setAutoProcessing(true);
        } else {
          setLoading(true);
        }
        setError("");
        setRecognizedPlate("");
        setConfidence(0);
        setHistory([]);

        try {
          const fd = new FormData();
          fd.append("file", blob, auto ? "auto_capture.jpg" : "capture.jpg");

          const res = await fetch(API.base + "/api/user/recognize_plate", {
            method: "POST",
            body: fd,
          });

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Plaka tanıma hatası oluştu");
          }

          const data = await res.json();
          setRecognizedPlate(data.plate_number);
          setConfidence(data.confidence);

          // Giriş kaydı oluştur ve geçmişi getir
          await registerEntry(data.plate_number, data.confidence);
          await fetchHistory(data.plate_number);

          // Otomatik modda başarılı tanıma sonrası durdur
          if (auto) {
            setAutoDetect(false);
          }
        } catch (err) {
          setError(err.message);
        } finally {
          sendingRef.current = false;
          setLoading(false);
          setAutoProcessing(false);
        }
      },
      "image/jpeg",
      0.92
    );
  };

  const handleLogout = () => {
    navigate("/");
  };

  return (
    <div className="user-page">
      <div className="user-header">
        <h1>Kullanıcı Paneli</h1>
        <button onClick={handleLogout} className="logout-btn">
          Çıkış Yap
        </button>
      </div>

      <div className="user-content">
        <div className="camera-section">
          <div className="card">
            <h2>Plaka Tanıma</h2>
            <button onClick={toggleCamera} className="camera-toggle-btn">
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
                  Sürekli algılama
                </label>
                {autoProcessing && (
                  <span className="muted">Otomatik algılama çalışıyor...</span>
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
                  className="camera-video"
                />
                <div className="capture-section">
                  <button 
                    onClick={captureAndRecognize} 
                    disabled={loading} 
                    className="capture-btn"
                  >
                    {loading ? "Tanınıyor..." : "Fotoğraf Çek ve Plaka Tanı"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="result-section">
          <div className="card">
            <h2>Tanıma Sonucu</h2>
            {recognizedPlate ? (
              <div className="result-success">
                <div className="plate-number">
                  <span className="label">Plaka:</span>
                  <span className="value">{recognizedPlate}</span>
                </div>
                <div className="confidence">
                  <span className="label">Güven:</span>
                  <span className="value">%{(confidence * 100).toFixed(1)}</span>
                </div>
                <div className="history">
                  <h3>Geçmiş Giriş / Çıkışlar</h3>
                  {history.length === 0 ? (
                    <p className="muted">Bu plaka için geçmiş kayıt bulunamadı.</p>
                  ) : (
                    <ul className="history-list">
                      {history.map((r) => (
                        <li key={r.id}>
                          <span>
                            Giriş:{" "}
                            {r.entry_time
                              ? r.entry_time.replace("T", " ").slice(0, 19)
                              : "-"}
                          </span>
                          {" | "}
                          <span>
                            Çıkış:{" "}
                            {r.exit_time
                              ? r.exit_time.replace("T", " ").slice(0, 19)
                              : "-"}
                          </span>
                          {" | "}
                          <span>
                            Ücret:{" "}
                            {typeof r.fee === "number"
                              ? `${r.fee.toFixed(2)} TL`
                              : "-"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            ) : (
              <div className="result-placeholder">
                <p>Plaka tanımak için kamerayı başlatın ve fotoğraf çekin</p>
              </div>
            )}
          </div>

          <div className="card">
            <h2>Giriş Yapan Araçlar (Bu Oturum)</h2>
            {sessionEntries.length === 0 ? (
              <p className="muted">Henüz giriş yapan araç yok.</p>
            ) : (
              <ul className="history-list">
                {sessionEntries.map((e, idx) => (
                  <li key={`${e.plate_number}-${e.time}-${idx}`}>
                    <span>Plaka: {e.plate_number}</span>
                    {" | "}
                    <span>
                      Zaman:{" "}
                      {e.time.replace("T", " ").slice(0, 19)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

