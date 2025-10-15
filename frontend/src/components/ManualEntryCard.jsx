import React, { useState } from "react";
import API from "../api";

export default function ManualEntryCard({ onCreated }) {
  const [plate, setPlate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("plate_number", plate.trim());

      const res = await fetch(API.base + API.manualEntry, {
        method: "POST",
        body: fd, // FormData gönderiyoruz, JSON değil
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Bir hata oluştu");
      }

      setPlate("");
      onCreated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Manuel Giriş</h2>
      <form onSubmit={onSubmit}>
        <label>Plaka</label>
        <input
          type="text"
          required
          value={plate}
          onChange={(e) => setPlate(e.target.value)}
        />
        <button disabled={loading}>
          {loading ? "Kaydediliyor..." : "Giriş Oluştur"}
        </button>
        {error && <p className="muted">{error}</p>}
      </form>
    </div>
  );
}
