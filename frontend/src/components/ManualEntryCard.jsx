import React, { useState } from "react";
import API from "../api";

export default function ManualEntryCard({ onCreated }) {
  const [plate, setPlate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Türkiye plaka formatı doğrulama regex'i
  const validateTurkishPlate = (plateNumber) => {
    // Regex: İl kodu (01-81) + Harf grubu (1-3 harf) + Sayı grubu (2-4 rakam)
    // Boşluklar opsiyonel
    const plateRegex = /^(0[1-9]|[1-7][0-9]|8[0-1])\s?[A-Z]{1,3}\s?\d{2,4}$/;
    return plateRegex.test(plateNumber.trim().toUpperCase());
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Plaka formatı doğrulama
    const normalizedPlate = plate.trim().toUpperCase();
    if (!validateTurkishPlate(normalizedPlate)) {
      setError("Lütfen Türkiye plaka formatına uygun geçerli bir plaka giriniz. Örnek: 34 ABC 1234");
      setLoading(false);
      return;
    }

    try {
      const fd = new FormData();
      fd.append("plate_number", normalizedPlate);

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
            placeholder="Örn: 34 ABC 1234"
            maxLength={12}
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
