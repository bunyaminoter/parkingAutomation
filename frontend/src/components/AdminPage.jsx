import React, { useCallback, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ManualEntryCard from "./ManualEntryCard";
import UploadCard from "./UploadCard";
import RecordsTable from "./RecordsTable";
import CameraCaptureCard from "./CameraCaptureCard";
import API from "../api";
import "../App.css";

export default function AdminPage() {
  const [refreshTick, setRefreshTick] = useState(0);
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

  return (
    <div className="container">
      <div className="admin-header">
        <h1>Admin Paneli - Parking Automation</h1>
        <div style={{ display: "flex", gap: "10px" }}>
          <button 
            onClick={() => navigate("/update-user-info")} 
            className="logout-btn"
            style={{ background: "var(--color-info)" }}
          >
            Bilgilerimi Güncelle
          </button>
          <button onClick={handleLogout} className="logout-btn">
            Çıkış Yap
          </button>
        </div>
      </div>
      <div className="admin-grid-top">
        <ManualEntryCard onCreated={triggerRefresh} />
        <UploadCard onCreated={triggerRefresh} />
        <CameraCaptureCard onCreated={triggerRefresh} />
      </div>
      <div className="admin-records-section">
        <RecordsTable forceRefreshKey={refreshTick} />
      </div>
    </div>
  );
}

