import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import "../App.css";

export default function UpdateUserInfoPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    // Session kontrolü ve kullanıcı bilgilerini al
    const checkSession = async () => {
      try {
        const response = await fetch(API.base + "/api/check_session", {
          method: "GET",
          credentials: "include",
        });

        if (!response.ok) {
          navigate("/");
          return;
        }

        const data = await response.json();
        if (data.success && data.user) {
          setUserInfo(data.user);
          setEmail(data.user.email);
        }
      } catch (err) {
        navigate("/");
      }
    };

    checkSession();
  }, [navigate]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    // Email doğrulama
    if (email && (!email.includes("@") || !email.split("@")[1].includes("."))) {
      setError("Geçerli bir e-posta adresi giriniz");
      setLoading(false);
      return;
    }

    // Şifre kontrolü
    if (newPassword && newPassword.length < 6) {
      setError("Şifre en az 6 karakter olmalıdır");
      setLoading(false);
      return;
    }

    if (newPassword && newPassword !== confirmPassword) {
      setError("Şifreler eşleşmiyor");
      setLoading(false);
      return;
    }

    try {
      const updateData = {};
      if (email && email !== userInfo.email) {
        updateData.email = email;
      }
      if (newPassword) {
        updateData.password = newPassword;
      }

      if (Object.keys(updateData).length === 0) {
        setError("Değişiklik yapmadınız");
        setLoading(false);
        return;
      }

      const response = await fetch(API.base + "/api/users/me/update", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(updateData),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setSuccess("Bilgileriniz başarıyla güncellendi");
        setNewPassword("");
        setConfirmPassword("");
        if (data.user) {
          setUserInfo(data.user);
          setEmail(data.user.email);
        }
      } else {
        setError(data.detail || "Güncelleme başarısız");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu");
    } finally {
      setLoading(false);
    }
  };

  if (!userInfo) {
    return (
      <div className="container">
        <div style={{ textAlign: "center", padding: "48px" }}>
          <div className="loading-spinner" style={{ margin: "0 auto 16px" }}></div>
          <p className="muted">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="admin-header">
        <h1>Kullanıcı Bilgilerini Güncelle</h1>
        <button onClick={() => navigate("/admin")} className="logout-btn">
          Geri Dön
        </button>
      </div>

      <div className="card" style={{ maxWidth: "600px", margin: "0 auto" }}>
        <h2>Bilgilerinizi Güncelleyin</h2>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message" style={{ background: "#4CAF50", color: "white", padding: "12px", borderRadius: "4px", marginBottom: "16px" }}>{success}</div>}

        <form onSubmit={handleUpdate} className="login-form">
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
            <label htmlFor="newPassword">Yeni Şifre (Değiştirmek istemiyorsanız boş bırakın):</label>
            <input
              type="password"
              id="newPassword"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={loading}
              minLength={6}
              placeholder="En az 6 karakter"
            />
          </div>

          {newPassword && (
            <div className="form-group">
              <label htmlFor="confirmPassword">Şifre Tekrar:</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                minLength={6}
                placeholder="Şifreyi tekrar girin"
              />
            </div>
          )}

          <button type="submit" disabled={loading} className="admin-login-btn" style={{ width: "100%" }}>
            {loading ? "Güncelleniyor..." : "Bilgileri Güncelle"}
          </button>
        </form>
      </div>
    </div>
  );
}

