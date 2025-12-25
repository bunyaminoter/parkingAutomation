import React, { useCallback, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ManualEntryCard from "./ManualEntryCard";
import UploadCard from "./UploadCard";
import RecordsTable from "./RecordsTable";
import CameraCaptureCard from "./CameraCaptureCard";
import Sidebar from "./Sidebar";
import API from "../api";
import "../App.css";

export default function AdminPage() {
  const [refreshTick, setRefreshTick] = useState(0);
  const [userInfo, setUserInfo] = useState(null);
  const [activeSection, setActiveSection] = useState("dashboard");
  const [updateEmail, setUpdateEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateError, setUpdateError] = useState("");
  const [updateSuccess, setUpdateSuccess] = useState("");
  const navigate = useNavigate();
  const triggerRefresh = useCallback(() => {
    setRefreshTick((tick) => tick + 1);
  }, []);

  // Sayfa yüklendiğinde session kontrolü yap
  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch(API.base + "/api/check_session", {
          method: "GET",
          credentials: "include", // Cookie'leri gönder
        });

        if (!response.ok) {
          // Session yoksa veya geçersizse login sayfasına yönlendir
          navigate("/");
          return;
        }
        
        const data = await response.json();
        if (data?.user) {
          setUserInfo({
            email: data.user.email,
            role: "Admin"
          });
          setUpdateEmail(data.user.email);
        }
      } catch (err) {
        // Hata durumunda login sayfasına yönlendir
        navigate("/");
      }
    };

    checkSession();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      // Backend'de session'ı temizle
      await fetch(API.base + "/api/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch (err) {
      console.error("Logout hatası:", err);
    } finally {
      // Her durumda login sayfasına yönlendir
      navigate("/");
    }
  };

  const handleSectionChange = (sectionId) => {
    setActiveSection(sectionId);
  };

  const handleUpdateInfo = async (e) => {
    e.preventDefault();
    setUpdateLoading(true);
    setUpdateError("");
    setUpdateSuccess("");

    // Email doğrulama
    if (updateEmail && (!updateEmail.includes("@") || !updateEmail.split("@")[1].includes("."))) {
      setUpdateError("Geçerli bir e-posta adresi giriniz");
      setUpdateLoading(false);
      return;
    }

    // Şifre kontrolü
    if (newPassword && newPassword.length < 6) {
      setUpdateError("Şifre en az 6 karakter olmalıdır");
      setUpdateLoading(false);
      return;
    }

    if (newPassword && newPassword !== confirmPassword) {
      setUpdateError("Şifreler eşleşmiyor");
      setUpdateLoading(false);
      return;
    }

    try {
      const updateData = {};
      if (updateEmail && updateEmail !== userInfo?.email) {
        updateData.email = updateEmail;
      }
      if (newPassword) {
        updateData.password = newPassword;
      }

      if (Object.keys(updateData).length === 0) {
        setUpdateError("Değişiklik yapmadınız");
        setUpdateLoading(false);
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
        setUpdateSuccess("Bilgileriniz başarıyla güncellendi");
        setNewPassword("");
        setConfirmPassword("");
        if (data.user) {
          setUserInfo({
            email: data.user.email,
            role: "Admin"
          });
          setUpdateEmail(data.user.email);
        }
      } else {
        setUpdateError(data.detail || "Güncelleme başarısız");
      }
    } catch (err) {
      setUpdateError("Bağlantı hatası oluştu");
    } finally {
      setUpdateLoading(false);
    }
  };

  const sidebarItems = [
    {
      id: "dashboard",
      key: "dashboard",
      label: "Ana Sayfa",
      icon: "🏠",
      onClick: () => handleSectionChange("dashboard")
    },
    {
      id: "manual-entry",
      key: "manual-entry",
      label: "Manuel Giriş",
      icon: "⌨️",
      onClick: () => handleSectionChange("manual-entry")
    },
    {
      id: "upload",
      key: "upload",
      label: "Dosya Yükleme",
      icon: "📁",
      onClick: () => handleSectionChange("upload")
    },
    {
      id: "camera",
      key: "camera",
      label: "Kamera Yakalama",
      icon: "📷",
      onClick: () => handleSectionChange("camera")
    },
    {
      id: "records",
      key: "records",
      label: "Park Kayıtları",
      icon: "📋",
      onClick: () => handleSectionChange("records")
    },
    {
      id: "update-info",
      key: "update-info",
      label: "Bilgilerimi Güncelle",
      icon: "👤",
      onClick: () => handleSectionChange("update-info")
    },
    {
      id: "logout",
      key: "logout",
      label: "Çıkış Yap",
      icon: "🚪",
      danger: true,
      onClick: handleLogout
    }
  ];

  const renderContent = () => {
    switch (activeSection) {
      case "dashboard":
        return (
          <div className="admin-dashboard">
            {/* Kullanıcı Bilgileri */}
            <div className="card" style={{ marginBottom: "24px" }}>
              <h2>Kullanıcı Bilgileri</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "16px" }}>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "4px" }}>E-posta</p>
                  <p style={{ fontWeight: "600", fontSize: "1rem", color: "var(--color-text-primary)" }}>
                    {userInfo?.email || "Yükleniyor..."}
                  </p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "4px" }}>Rol</p>
                  <p style={{ fontWeight: "600", fontSize: "1rem", color: "var(--color-text-primary)" }}>
                    {userInfo?.role || "Admin"}
                  </p>
                </div>
              </div>
            </div>

            {/* Otopark Bilgileri */}
            <div className="card" style={{ marginBottom: "24px" }}>
              <h2>Otopark Bilgileri</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Otopark Adı</p>
                  <p style={{ fontWeight: "700", fontSize: "1.25rem", color: "var(--color-primary)" }}>La Parque</p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Lokasyon / Adres</p>
                  <p style={{ fontWeight: "500", fontSize: "1rem", color: "var(--color-text-primary)" }}>
                    Karadeniz Teknik Üniversitesi OF Fakültesi No: 061, Of, Trabzon
                  </p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Kat Sayısı</p>
                  <p style={{ fontWeight: "600", fontSize: "1.125rem", color: "var(--color-text-primary)" }}>2 Kat</p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Toplam Kapasite</p>
                  <p style={{ fontWeight: "600", fontSize: "1.125rem", color: "var(--color-text-primary)" }}>150 Araç</p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Saatlik Ücret</p>
                  <p style={{ fontWeight: "700", fontSize: "1.25rem", color: "var(--color-success)" }}>120.00 ₺</p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Açılış – Kapanış Saatleri</p>
                  <p style={{ fontWeight: "500", fontSize: "1rem", color: "var(--color-text-primary)" }}>07:00 - 23:00</p>
                </div>
                <div>
                  <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginBottom: "8px" }}>Otopark Durumu</p>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "6px 16px",
                      borderRadius: "20px",
                      fontSize: "0.875rem",
                      fontWeight: "600",
                      background: "#d1fae5",
                      color: "#059669",
                      border: "1px solid #10b981"
                    }}
                  >
                    ✓ Açık
                  </span>
                </div>
              </div>
            </div>

          </div>
        );
      case "manual-entry":
        return (
          <div className="admin-section-content">
            <ManualEntryCard onCreated={triggerRefresh} />
          </div>
        );
      case "upload":
        return (
          <div className="admin-section-content">
            <UploadCard onCreated={triggerRefresh} />
          </div>
        );
      case "camera":
        return (
          <div className="admin-section-content">
            <CameraCaptureCard onCreated={triggerRefresh} />
          </div>
        );
      case "records":
        return (
          <div className="admin-section-content">
            <RecordsTable forceRefreshKey={refreshTick} />
          </div>
        );
      case "update-info":
        return (
          <div className="admin-section-content">
            <div className="card">
              <h2>Bilgilerinizi Güncelleyin</h2>

              {updateError && <div className="error-message">{updateError}</div>}
              {updateSuccess && (
                <div className="success-message" style={{ background: "#4CAF50", color: "white", padding: "12px", borderRadius: "4px", marginBottom: "16px" }}>
                  {updateSuccess}
                </div>
              )}

              <form onSubmit={handleUpdateInfo}>
                <div className="form-group">
                  <label htmlFor="email">E-posta:</label>
                  <input
                    type="email"
                    id="email"
                    value={updateEmail}
                    onChange={(e) => setUpdateEmail(e.target.value)}
                    required
                    disabled={updateLoading}
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
                    disabled={updateLoading}
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
                      disabled={updateLoading}
                      minLength={6}
                      placeholder="Şifreyi tekrar girin"
                    />
                  </div>
                )}

                <button type="submit" disabled={updateLoading} style={{ width: "100%" }}>
                  {updateLoading ? (
                    <>
                      <span className="loading-spinner"></span>
                      Güncelleniyor...
                    </>
                  ) : (
                    "Bilgileri Güncelle"
                  )}
                </button>
              </form>
            </div>
          </div>
        );
      default:
        return (
          <div className="admin-grid-top">
            <ManualEntryCard onCreated={triggerRefresh} />
            <UploadCard onCreated={triggerRefresh} />
            <CameraCaptureCard onCreated={triggerRefresh} />
          </div>
        );
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar 
        items={sidebarItems}
        activeItem={activeSection}
        userInfo={userInfo}
      />
      <div className="main-content" style={{ flex: 1, width: "100%" }}>
        <div className="container">
          <div className="admin-header">
            <h1>Admin Paneli - Parking Automation</h1>
          </div>
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

