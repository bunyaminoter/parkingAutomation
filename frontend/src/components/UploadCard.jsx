import React, { useState } from "react";
import API from "../api";

export default function UploadCard({ onCreated }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("file", file);

      const res = await fetch(API.base + API.uploadImage, {
        method: "POST",
        body: fd, // FormData gönderiliyor
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Yükleme hatası oluştu");
      }

      // Başarılı olursa input sıfırlanır
      setFile(null);
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
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button disabled={!file || loading}>
          {loading ? "Yükleniyor..." : "Yükle"}
        </button>
        {error && <p className="muted">{error}</p>}
      </form>
    </div>
  );
}
