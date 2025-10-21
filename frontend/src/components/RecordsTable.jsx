import React, { useEffect, useState } from "react";
import API from "../api";
import { fetchJSON } from "../utils";

export default function RecordsTable({ refreshKey, onRefresh }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completing, setCompleting] = useState(new Set());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchJSON(API.base + API.getRecords);
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [refreshKey]);

  const handleComplete = async (recordId) => {
    setCompleting(prev => new Set(prev).add(recordId));
    try {
      await fetchJSON(API.base + API.completeRecord(recordId), {
        method: "PUT",
        headers: { "Content-Type": "application/json" }
        // fee göndermiyoruz, backend otomatik hesaplayacak
      });
      onRefresh?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setCompleting(prev => {
        const newSet = new Set(prev);
        newSet.delete(recordId);
        return newSet;
      });
    }
  };

  return (
    <div className="card">
      <h2>Park Kayıtları</h2>
      {loading ? (
        <p className="muted">Yükleniyor...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Plaka</th>
              <th>Giriş</th>
              <th>Çıkış</th>
              <th>Ücret</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.plate_number || "-"}</td>
                <td>{r.entry_time?.replace("T", " ").slice(0, 19)}</td>
                <td>
                  {r.exit_time
                    ? r.exit_time.replace("T", " ").slice(0, 19)
                    : <span className="pill status-in">İçeride</span>}
                </td>
                <td>{r.fee?.toFixed?.(2) ?? "0.00"}</td>
                <td>
                  {!r.exit_time && (
                    <button
                      onClick={() => handleComplete(r.id)}
                      disabled={completing.has(r.id)}
                      className="btn-small"
                    >
                      {completing.has(r.id) ? "Çıkış yapılıyor..." : "Çıkış Yap"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {error && <p className="muted">{error}</p>}
    </div>
  );
}
