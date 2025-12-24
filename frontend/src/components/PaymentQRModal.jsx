import React, { useEffect, useState } from "react";
import QRCode from "qrcode";
import API from "../api";
import "./PaymentQRModal.css";

export default function PaymentQRModal({ payment, onClose, onPaymentConfirmed }) {
  const [countdown, setCountdown] = useState(30);
  const [autoConfirming, setAutoConfirming] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(payment?.status || "PENDING");
  const [error, setError] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState("");

  // QR kod oluştur
  useEffect(() => {
    if (!payment) return;
    
    const generateQR = async () => {
      try {
        const qrText = payment.qr_json || JSON.stringify(payment.qr_data || {});
        const dataUrl = await QRCode.toDataURL(qrText, {
          width: 256,
          margin: 2,
          color: {
            dark: "#000000",
            light: "#FFFFFF"
          }
        });
        setQrDataUrl(dataUrl);
      } catch (err) {
        console.error("QR generation error:", err);
        setError("QR kod oluşturulamadı");
      }
    };
    
    generateQR();
  }, [payment]);

  useEffect(() => {
    if (!payment || payment.status !== "PENDING") return;

    // Otomatik onay başlat
    const startAutoConfirm = async () => {
      setAutoConfirming(true);
      
      // 30 saniye geri sayım
      for (let i = 30; i > 0; i--) {
        setCountdown(i);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      try {
        // Otomatik onay endpoint'ini çağır
        const response = await fetch(API.base + `/api/payments/${payment.id}/auto-confirm`, {
          method: "POST",
          credentials: "include",
        });

        if (response.ok) {
          const data = await response.json();
          setPaymentStatus("PAID");
          if (onPaymentConfirmed) {
            onPaymentConfirmed(data);
          }
        } else {
          const errorData = await response.json();
          setError(errorData.detail || "Ödeme onaylanamadı");
        }
      } catch (err) {
        setError("Bağlantı hatası oluştu");
      } finally {
        setAutoConfirming(false);
      }
    };

    startAutoConfirm();
  }, [payment, onPaymentConfirmed]);

  const handleManualConfirm = async () => {
    try {
      setError("");
      const response = await fetch(API.base + `/api/payments/${payment.id}/confirm`, {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setPaymentStatus("PAID");
        if (onPaymentConfirmed) {
          onPaymentConfirmed(data);
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Ödeme onaylanamadı");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu");
    }
  };

  if (!payment) return null;

  return (
    <div className="qr-modal-overlay" onClick={onClose}>
      <div className="qr-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="qr-modal-header">
          <h2>Ödeme İşlemi</h2>
          <button className="qr-modal-close" onClick={onClose}>×</button>
        </div>

        <div className="qr-modal-body">
          {paymentStatus === "PENDING" && (
            <>
              <div className="qr-info">
                <p className="qr-amount">
                  <strong>Ödeme Tutarı:</strong> {payment.amount} {payment.currency}
                </p>
                <p className="qr-reference">
                  <strong>Referans:</strong> {payment.reference}
                </p>
              </div>

              <div className="qr-code-container">
                {qrDataUrl ? (
                  <img src={qrDataUrl} alt="QR Code" style={{ maxWidth: "100%", height: "auto" }} />
                ) : (
                  <div style={{ padding: "40px", textAlign: "center", color: "#6b7280" }}>
                    QR kod yükleniyor...
                  </div>
                )}
              </div>

              <div className="qr-instructions">
                <p>QR kodu banka uygulamanızla okutun ve ödemeyi tamamlayın.</p>
                {autoConfirming && (
                  <p className="qr-countdown">
                    Otomatik onay: {countdown} saniye...
                  </p>
                )}
              </div>

              {error && <div className="qr-error">{error}</div>}

              <div className="qr-actions">
                <button
                  className="qr-confirm-btn"
                  onClick={handleManualConfirm}
                  disabled={autoConfirming}
                >
                  {autoConfirming ? "Bekleniyor..." : "Ödemeyi Tamamladım"}
                </button>
                <button className="qr-cancel-btn" onClick={onClose}>
                  İptal
                </button>
              </div>
            </>
          )}

          {paymentStatus === "PAID" && (
            <div className="qr-success">
              <div className="qr-success-icon">✓</div>
              <h3>Ödeme Başarılı!</h3>
              <p>Bariyer açılıyor...</p>
              <button className="qr-close-btn" onClick={onClose}>
                Kapat
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

