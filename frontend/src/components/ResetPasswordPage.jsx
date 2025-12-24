import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import API from "../api";
import "./LoginPage.css";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);

  useEffect(() => {
    // Token'ı doğrula
    const verifyToken = async () => {
      if (!token) {
        setValidating(false);
        setTokenValid(false);
        return;
      }

      try {
        const response = await fetch(API.base + `/api/verify-reset-token/${token}`, {
          method: "GET",
        });

        const data = await response.json();

        if (response.ok && data.valid) {
          setTokenValid(true);
        } else {
          setTokenValid(false);
          setError(data.message || "Geçersiz veya süresi dolmuş token");
        }
      } catch (err) {
        setTokenValid(false);
        setError("Token doğrulanırken bir hata oluştu");
      } finally {
        setValidating(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    // Şifre kontrolü
    if (newPassword.length < 6) {
      setError("Şifre en az 6 karakter olmalıdır");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Şifreler eşleşmiyor");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(API.base + "/api/reset-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setSuccess(true);
        setTimeout(() => {
          navigate("/");
        }, 3000);
      } else {
        setError(data.detail || "Şifre sıfırlama başarısız");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu");
    } finally {
      setLoading(false);
    }
  };

  if (validating) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>Parking Automation</h1>
          <div style={{ textAlign: "center", padding: "20px" }}>
            <div className="loading-spinner" style={{ margin: "0 auto" }}></div>
            <p>Token doğrulanıyor...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!tokenValid) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>Parking Automation</h1>
          <h2>Şifre Sıfırlama</h2>
          {error && <div className="error-message">{error}</div>}
          <p style={{ textAlign: "center", marginTop: "20px" }}>
            Geçersiz veya süresi dolmuş token. Lütfen yeni bir şifre sıfırlama isteği yapın.
          </p>
          <button
            onClick={() => navigate("/")}
            className="admin-login-btn"
            style={{ marginTop: "20px" }}
          >
            Giriş Sayfasına Dön
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Parking Automation</h1>
        <h2>Yeni Şifre Belirle</h2>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">
            Şifreniz başarıyla güncellendi. 3 saniye sonra giriş sayfasına yönlendirileceksiniz.
          </div>
        )}

        {!success && (
          <form onSubmit={handleResetPassword} className="login-form">
            <div className="form-group">
              <label htmlFor="newPassword">Yeni Şifre:</label>
              <input
                type="password"
                id="newPassword"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                disabled={loading}
                minLength={6}
                placeholder="En az 6 karakter"
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Şifre Tekrar:</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                minLength={6}
                placeholder="Şifreyi tekrar girin"
              />
            </div>

            <button type="submit" disabled={loading} className="admin-login-btn">
              {loading ? "Güncelleniyor..." : "Şifreyi Güncelle"}
            </button>
          </form>
        )}

        {!success && (
          <button
            onClick={() => navigate("/")}
            className="user-login-btn"
            style={{ marginTop: "10px" }}
          >
            İptal
          </button>
        )}
      </div>
    </div>
  );
}

