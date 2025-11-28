import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../api";
import { fetchJSON } from "../utils";

export default function RecordsTable({ forceRefreshKey = 0 }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [socketState, setSocketState] = useState("connecting");
  const [completing, setCompleting] = useState(new Set());
  const reconnectTimer = useRef();

  const wsUrl = useMemo(() => {
    const base = API.wsBase || API.base.replace(/^http/, "ws");
    return base + API.recordsStream;
  }, []);

  const fetchLatest = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchJSON(API.base + API.getRecords);
      setRows(data);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ws;

    const connect = () => {
      setSocketState("connecting");
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setSocketState("connected");
        fetchLatest();
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload?.type === "records" && Array.isArray(payload.payload)) {
            setRows(payload.payload);
            setLoading(false);
            setError("");
          }
        } catch (err) {
          console.error("WebSocket parse error:", err);
        }
      };

      ws.onerror = () => {
        setSocketState("error");
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };

      ws.onclose = () => {
        setSocketState("disconnected");
        reconnectTimer.current = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [wsUrl, fetchLatest]);

  useEffect(() => {
    fetchLatest();
  }, [fetchLatest, forceRefreshKey]);

  const handleComplete = async (recordId) => {
    setCompleting((prev) => new Set(prev).add(recordId));
    try {
      await fetchJSON(API.base + API.completeRecord(recordId), {
        method: "PUT",
        headers: { "Content-Type": "application/json" }
      });
      await fetchLatest();
    } catch (err) {
      setError(err.message);
    } finally {
      setCompleting((prev) => {
        const newSet = new Set(prev);
        newSet.delete(recordId);
        return newSet;
      });
    }
  };

  const statusText = {
    connecting: "Canlı bağlantı kuruluyor...",
    connected: "Canlı veri",
    disconnected: "Bağlantı koptu, yeniden deneniyor...",
    error: "WebSocket hatası",
  }[socketState] || "";

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <h2>Park Kayıtları</h2>
        <span
          className="muted"
          style={{ color: socketState === "connected" ? "#28a745" : undefined }}
        >
          {statusText}
        </span>
      </div>
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
