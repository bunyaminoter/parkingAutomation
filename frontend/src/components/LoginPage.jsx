import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import "./LoginPage.css";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showForgotPassword, setShowForgotPassword] = useState(false);
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

    try {
      const formData = new FormData();
      formData.append("username", username);
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
            <label htmlFor="username">Kullanıcı Adı:</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
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
          <p><strong>Admin Girişi:</strong> Kullanıcı adı ve şifre gerekli</p>
          <p><strong>Kullanıcı Girişi:</strong> Şifre gerektirmez, sadece plaka tanıma</p>
        </div>
      </div>

      {/* Şifremi Unuttum Modal */}
      {showForgotPassword && (
        <div className="modal-overlay" onClick={() => setShowForgotPassword(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Şifremi Unuttum</h3>
            <p>
              Şifrenizi güncellemek için lütfen{" "}
              <a href="mailto:bunyaminoter@gmail.com" className="email-link">
                bunyaminoter@gmail.com
              </a>{" "}
              ile iletişime geçiniz.
            </p>
            <button 
              className="modal-close-btn"
              onClick={() => setShowForgotPassword(false)}
            >
              Kapat
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

