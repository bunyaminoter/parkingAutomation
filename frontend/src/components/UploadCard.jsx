import React, { useState } from "react";
import API from "../api";

export default function UploadCard({ onCreated }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Lütfen bir dosya seçin");
      return;
    }
    setLoading(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("file", file);

      const res = await fetch(API.base + API.uploadImage, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Yükleme hatası oluştu");
      }

      setFile(null);
      const fileInput = document.getElementById("file-input");
      if (fileInput) fileInput.value = "";
      onCreated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Resimden Plaka Tanıma</h2>
      <form onSubmit={onSubmit}>
        <div className="form-group">
          <label htmlFor="file-input">Resim Dosyası</label>
          <input
            id="file-input"
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={loading}
          />
          {file && (
            <div style={{ 
              marginTop: "8px", 
              fontSize: "0.875rem", 
              color: "var(--color-text-secondary)",
              padding: "8px 12px",
              background: "var(--color-bg-secondary)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)"
            }}>
              Seçilen: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(2)} KB)
            </div>
          )}
        </div>
        <button type="submit" disabled={!file || loading}>
          {loading ? (
            <>
              <span className="loading-spinner"></span>
              Yükleniyor...
            </>
          ) : (
            "Yükle ve Tanı"
          )}
        </button>
        {error && <div className="error-message">{error}</div>}
      </form>
    </div>
  );
}
