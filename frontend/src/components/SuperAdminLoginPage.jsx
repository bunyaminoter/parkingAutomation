import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import "./LoginPage.css";

export default function SuperAdminLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
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

      const response = await fetch(API.base + API.superAdminLogin, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      const data = await response.json();

      if (response.ok && data.success) {
        navigate("/panel");
      } else {
        setError(data.detail || "Giriş başarısız");
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
        <h2>Üst Admin Girişi</h2>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleLogin} className="login-form">
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
          </div>

          <button type="submit" disabled={loading} className="admin-login-btn">
            {loading ? "Giriş yapılıyor..." : "Üst Admin Paneli"}
          </button>
        </form>
      </div>
    </div>
  );
}



