import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import "./LoginPage.css";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState("");
  const [forgotPasswordLoading, setForgotPasswordLoading] = useState(false);
  const [forgotPasswordMessage, setForgotPasswordMessage] = useState("");
  const [devModeToken, setDevModeToken] = useState(null);
  const [devModeLink, setDevModeLink] = useState("");
  const navigate = useNavigate();

  // Sayfa yüklendiğinde session kontrolü yap
  // Sadece "beni hatırla" işaretliyse otomatik login yap
  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch(API.base + "/api/check_session", {
          method: "GET",
          credentials: "include", // Cookie'leri gönder
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.remember_me) {
            // Sadece "beni hatırla" işaretliyse otomatik olarak admin paneline yönlendir
            navigate("/admin");
          }
          // remember_me=false ise otomatik login yapma, kullanıcı manuel giriş yapmalı
        }
      } catch (err) {
        // Session yoksa veya hata varsa, login sayfasında kal
        // Session kontrolü başarısız
      }
    };

    checkSession();
  }, [navigate]);

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Email doğrulama
    if (!email.includes("@") || !email.split("@")[1].includes(".")) {
      setError("Geçerli bir e-posta adresi giriniz");
      setLoading(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", password);
      formData.append("remember_me", rememberMe.toString());

      const response = await fetch(API.base + "/api/login", {
        method: "POST",
        body: formData,
        credentials: "include", // Cookie'leri almak için
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Admin paneline yönlendir
        navigate("/admin");
      } else {
        setError(data.detail || "Giriş başarısız");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setForgotPasswordLoading(true);
    setForgotPasswordMessage("");
    setError("");

    // Email doğrulama
    if (!forgotPasswordEmail.includes("@") || !forgotPasswordEmail.split("@")[1].includes(".")) {
      setError("Geçerli bir e-posta adresi giriniz");
      setForgotPasswordLoading(false);
      return;
    }

    try {
      const response = await fetch(API.base + "/api/forgot-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: forgotPasswordEmail }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Development modunda token ve link'i göster
        if (data.dev_mode && data.token) {
          setDevModeToken(data.token);
          setDevModeLink(data.reset_link);
          setForgotPasswordMessage(
            "Development modunda çalışıyorsunuz. Email gönderilmedi. " +
            "Aşağıdaki linki kullanarak şifrenizi sıfırlayabilirsiniz."
          );
        } else {
          setForgotPasswordMessage(data.message);
          setForgotPasswordEmail("");
          setTimeout(() => {
            setShowForgotPassword(false);
            setForgotPasswordMessage("");
            setDevModeToken(null);
            setDevModeLink("");
          }, 5000);
        }
      } else {
        setError(data.detail || "Bir hata oluştu");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu");
    } finally {
      setForgotPasswordLoading(false);
    }
  };

  const handleUserLogin = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(API.base + "/api/user_login");
      const data = await response.json();

      if (response.ok && data.success) {
        // Kullanıcı sayfasına yönlendir
        navigate("/user");
      } else {
        setError("Kullanıcı girişi başarısız");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Parking Automation</h1>
        <h2>Giriş Yap</h2>
        
        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleAdminLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="email">E-posta:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              placeholder="ornek@email.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Şifre:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
            <a 
              href="#" 
              className="forgot-password-link"
              onClick={(e) => {
                e.preventDefault();
                setShowForgotPassword(true);
              }}
            >
              Şifremi unuttum
            </a>
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={loading}
              />
              <span>Beni hatırla</span>
            </label>
          </div>

          <button type="submit" disabled={loading} className="admin-login-btn">
            {loading ? "Giriş yapılıyor..." : "Admin Paneli"}
          </button>
        </form>

        <div className="divider">
          <span>veya</span>
        </div>

        <button 
          onClick={handleUserLogin} 
          disabled={loading} 
          className="user-login-btn"
        >
          {loading ? "Yönlendiriliyor..." : "Kullanıcı Girişi"}
        </button>

        <div className="login-info">
          <p><strong>Admin Girişi:</strong> E-posta ve şifre gerekli</p>
          <p><strong>Kullanıcı Girişi:</strong> Şifre gerektirmez, sadece plaka tanıma</p>
        </div>
      </div>

      {/* Şifremi Unuttum Modal */}
      {showForgotPassword && (
        <div className="modal-overlay" onClick={() => setShowForgotPassword(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Şifremi Unuttum</h3>
            {forgotPasswordMessage && (
              <div className="success-message">{forgotPasswordMessage}</div>
            )}
            {devModeToken && devModeLink && (
              <div style={{
                marginTop: "20px",
                padding: "16px",
                background: "#f0f9ff",
                border: "1px solid #0ea5e9",
                borderRadius: "8px",
                textAlign: "left"
              }}>
                <p style={{ marginBottom: "10px", fontWeight: "600", color: "#0c4a6e" }}>
                  🔧 Development Modu - Şifre Sıfırlama Linki:
                </p>
                <a
                  href={devModeLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "block",
                    wordBreak: "break-all",
                    color: "#0284c7",
                    textDecoration: "underline",
                    marginBottom: "10px"
                  }}
                >
                  {devModeLink}
                </a>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(devModeLink);
                    alert("Link kopyalandı!");
                  }}
                  style={{
                    padding: "8px 16px",
                    background: "#0284c7",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                    fontSize: "0.875rem"
                  }}
                >
                  Linki Kopyala
                </button>
                <p style={{ marginTop: "10px", fontSize: "0.75rem", color: "#64748b" }}>
                  Token: {devModeToken}
                </p>
              </div>
            )}
            {!forgotPasswordMessage && !devModeToken && (
              <>
                <p>E-posta adresinizi girin, size şifre sıfırlama bağlantısı gönderelim.</p>
                <form onSubmit={handleForgotPassword} className="forgot-password-form">
                  <div className="form-group">
                    <label htmlFor="forgot-email">E-posta:</label>
                    <input
                      type="email"
                      id="forgot-email"
                      value={forgotPasswordEmail}
                      onChange={(e) => setForgotPasswordEmail(e.target.value)}
                      required
                      disabled={forgotPasswordLoading}
                      placeholder="ornek@email.com"
                    />
                  </div>
                  <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
                    <button 
                      type="submit"
                      disabled={forgotPasswordLoading}
                      className="modal-submit-btn"
                    >
                      {forgotPasswordLoading ? "Gönderiliyor..." : "Gönder"}
                    </button>
                    <button 
                      type="button"
                      className="modal-close-btn"
                      onClick={() => {
                        setShowForgotPassword(false);
                        setForgotPasswordEmail("");
                        setForgotPasswordMessage("");
                        setDevModeToken(null);
                        setDevModeLink("");
                      }}
                    >
                      İptal
                    </button>
                  </div>
                </form>
              </>
            )}
            {forgotPasswordMessage && !devModeToken && (
              <button 
                className="modal-close-btn"
                onClick={() => {
                  setShowForgotPassword(false);
                  setForgotPasswordEmail("");
                  setForgotPasswordMessage("");
                  setDevModeToken(null);
                  setDevModeLink("");
                }}
                style={{ marginTop: "20px" }}
              >
                Kapat
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

