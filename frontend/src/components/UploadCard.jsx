import React, { useState } from "react";
import API from "../api";

export default function UploadCard({ type, onCreated }) {
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

      const url = type === "image" ? API.uploadImage : API.uploadVideo;

      const res = await fetch(API.base + url, {
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
      <h2>{type === "image" ? "Resimden Plaka Tanıma" : "Kameradan Plaka Tanıma (Eklenecek)"}</h2>
      <form onSubmit={onSubmit}>
        <input
          type="file"
          accept={type === "image" ? "image/*" : "video/*"}
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
