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
      fd.append("plate_number", plate.trim().toUpperCase());

      const res = await fetch(API.base + API.manualEntry, {
        method: "POST",
        body: fd,
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
        <div className="form-group">
          <label htmlFor="plate">Plaka Numarası</label>
          <input
            id="plate"
            type="text"
            required
            value={plate}
            onChange={(e) => setPlate(e.target.value.toUpperCase())}
            placeholder="Örn: 34ABC123"
            maxLength={10}
            disabled={loading}
            style={{ 
              textTransform: "uppercase", 
              letterSpacing: "1px", 
              fontSize: "16px", 
              fontWeight: "600",
              fontFamily: "monospace"
            }}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? (
            <>
              <span className="loading-spinner"></span>
              Kaydediliyor...
            </>
          ) : (
            "Giriş Oluştur"
          )}
        </button>
        {error && <div className="error-message">{error}</div>}
      </form>
    </div>
  );
}
