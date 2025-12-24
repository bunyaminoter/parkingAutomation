import React, { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import { fetchJSON } from "../utils";
import PaymentQRModal from "./PaymentQRModal";
import "./UserPage.css";

const AUTO_CAPTURE_INTERVAL = 3000; // ms

const InvoiceTicket = ({ record }) => {
  //  ÇIKIŞ KONTROLÜ
  if (!record || !record.exit_time) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("tr-TR", {
      day: 'numeric', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };

  return (
    <div className="invoice-ticket fade-in">
      <div className="invoice-header">
        <h3>La Parque</h3>
        <p>HİZMET FATURASI</p>
      </div>
      <div className="invoice-body">
        <div className="invoice-row">
          <span className="inv-label">PLAKA NO:</span>
          <span className="inv-value">{record.plate_number}</span>
        </div>
        <div className="invoice-row">
          <span className="inv-label">GİRİŞ ZAMANI:</span>
          <span className="inv-value">{formatDate(record.entry_time)}</span>
        </div>
        <div className="invoice-row">
          <span className="inv-label">ÇIKIŞ ZAMANI:</span>
          <span className="inv-value">{formatDate(record.exit_time)}</span>
        </div>

        <div className="invoice-divider">--------------------------------</div>

        <div className="invoice-row total">
          <span className="inv-label">TOPLAM TUTAR:</span>
          <span className="inv-value">
            {typeof record.fee === "number" ? `${record.fee.toFixed(2)} ₺` : "0.00 ₺"}
          </span>
        </div>
      </div>
      <div className="invoice-footer">
        <p>Bizi tercih ettiğiniz için teşekkürler.</p>
        <p>La Parque Otopark İşletmeleri</p>
      </div>
    </div>
  );
};
// ------------------------------------

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
  const [selectedPayment, setSelectedPayment] = useState(null);
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
      // Giriş/Çıkış isteği gönder
      const response = await fetch(API.base + API.manualEntry, {
        method: "POST",
        body: fd,
      });
      
      if (!response.ok) {
        throw new Error("Giriş/Çıkış işlemi başarısız");
      }
      
      const result = await response.json();
      
      // Oturum listesine ekle (sadece giriş için)
      if (result.action === "entry") {
        setSessionEntries((prev) => [
          { plate_number: plate, time: new Date().toISOString() },
          ...prev,
        ]);
      }
      
      return result;
    } catch (e) {
      console.error(e);
      return null;
    }
  };

  const handlePaymentConfirmed = async (paymentData) => {
    // Ödeme tamamlandı, geçmişi yenile
    if (recognizedPlate) {
      await fetchHistory(recognizedPlate);
    }
    // Modal'ı kapat
    setTimeout(() => {
      setSelectedPayment(null);
    }, 2000);
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

          // Giriş/Çıkış işlemini yap ve geçmişi güncelle
          const entryResult = await registerEntry(data.plate_number, data.confidence);
          
          // Eğer çıkış yapıldıysa ve payment varsa QR modal'ı göster
          if (entryResult && entryResult.action === "exit" && entryResult.payment) {
            setSelectedPayment(entryResult.payment);
          }
          
          await fetchHistory(data.plate_number);

          // Otomatik modda ise durdur (tek seferlik işlem)
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
                    onClick={() => captureAndRecognize(false)}
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

                {/* --- SADECE ÇIKIŞ YAPAN ARAÇLAR İÇİN FATURA --- */}
                {history.length > 0 && (
                   <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'center' }}>
                     <InvoiceTicket record={history[0]} />
                   </div>
                )}
                {/* ----------------------------------------------- */}

                <div className="history">
                  <h3>Geçmiş Kayıtlar</h3>
                  {history.length === 0 ? (
                    <p className="muted" style={{ textAlign: "center", padding: "20px" }}>
                      Bu plaka için geçmiş kayıt bulunamadı.
                    </p>
                  ) : (
                    <ul className="history-list">
                      {history.map((r) => (
                        <li key={r.id}>
                          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontWeight: "600", color: "var(--color-text-primary)", fontSize: "0.875rem" }}>
                                Giriş: {r.entry_time
                                  ? r.entry_time.replace("T", " ").slice(0, 19)
                                  : "-"}
                              </span>
                              {r.exit_time && (
                                <span style={{ fontWeight: "600", color: "var(--color-text-primary)", fontSize: "0.875rem" }}>
                                  Çıkış: {r.exit_time.replace("T", " ").slice(0, 19)}
                                </span>
                              )}
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{
                                fontSize: "0.75rem",
                                color: "var(--color-text-muted)",
                                padding: "4px 8px",
                                background: r.exit_time ? "var(--color-bg-secondary)" : "#d1fae5",
                                borderRadius: "4px",
                                fontWeight: "500"
                              }}>
                                {r.exit_time ? "Tamamlandı" : "Aktif"}
                              </span>
                              <span style={{ fontWeight: "700", color: "var(--color-primary)", fontSize: "1rem" }}>
                                {typeof r.fee === "number"
                                  ? `${r.fee.toFixed(2)} ₺`
                                  : "-"}
                              </span>
                            </div>
                          </div>
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
              <p className="muted" style={{ textAlign: "center", padding: "20px" }}>
                Henüz giriş yapan araç yok.
              </p>
            ) : (
              <ul className="history-list">
                {sessionEntries.map((e, idx) => (
                  <li key={`${e.plate_number}-${e.time}-${idx}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: "700", fontSize: "1rem", letterSpacing: "1px", color: "var(--color-primary)", fontFamily: "monospace" }}>
                        {e.plate_number}
                      </span>
                      <span style={{ fontSize: "0.875rem", color: "var(--color-text-secondary)" }}>
                        {e.time.replace("T", " ").slice(0, 19)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
      
      {/* Payment QR Modal */}
      {selectedPayment && (
        <PaymentQRModal
          payment={selectedPayment}
          onClose={() => setSelectedPayment(null)}
          onPaymentConfirmed={handlePaymentConfirmed}
        />
      )}
    </div>
  );
}