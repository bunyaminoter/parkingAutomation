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
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

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

  const handleDelete = async (recordId) => {
    const confirmDelete = window.confirm(
      `ID=${recordId} olan park kaydını silmek istediğinize emin misiniz?`
    );
    if (!confirmDelete) return;

    try {
      await fetchJSON(API.base + API.deleteRecord(recordId), {
        method: "DELETE",
      });
      await fetchLatest();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditPlate = async (record) => {
    const current = record.plate_number || "";
    const next = window.prompt("Yeni plaka numarasını girin:", current);
    if (!next || next.trim() === "" || next.trim() === current.trim()) {
      return;
    }
    try {
      await fetchJSON(API.base + API.updatePlate(record.id), {
        method: "PUT",
        body: JSON.stringify({ plate_number: next.trim().toUpperCase() }),
      });
      await fetchLatest();
    } catch (err) {
      setError(err.message);
    }
  };

  const statusConfig = {
    connecting: { text: "Bağlanıyor...", color: "var(--color-warning)", bg: "#fef3c7" },
    connected: { text: "Canlı", color: "var(--color-success)", bg: "#d1fae5" },
    disconnected: { text: "Bağlantı koptu", color: "var(--color-warning)", bg: "#fef3c7" },
    error: { text: "Hata", color: "var(--color-danger)", bg: "#fee2e2" },
  };

  const status = statusConfig[socketState] || statusConfig.connecting;

  // Pagination hesaplamaları
  const totalPages = Math.ceil(rows.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentRows = rows.slice(startIndex, endIndex);

  // Sayfa değiştiğinde en üste kaydır
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
          marginBottom: "20px",
          flexWrap: "wrap",
        }}
      >
        <h2>Park Kayıtları {rows.length > 0 && <span style={{ fontSize: "0.875rem", fontWeight: "400", color: "var(--color-text-muted)" }}>({rows.length} kayıt)</span>}</h2>
        <span
          style={{
            color: status.color,
            fontWeight: "600",
            fontSize: "0.75rem",
            padding: "6px 12px",
            background: status.bg,
            borderRadius: "12px",
            border: `1px solid ${status.color}`,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {status.text}
        </span>
      </div>
      {loading && rows.length === 0 ? (
        <div style={{ textAlign: "center", padding: "48px" }}>
          <div className="loading-spinner" style={{ margin: "0 auto 16px", borderColor: "var(--color-primary) rgba(0,0,0,0.1)", borderTopColor: "var(--color-primary)" }}></div>
          <p className="muted">Yükleniyor...</p>
        </div>
      ) : rows.length === 0 ? (
        <div style={{ textAlign: "center", padding: "48px" }}>
          <p className="muted" style={{ fontSize: "1rem" }}>Henüz kayıt bulunmuyor</p>
        </div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Plaka</th>
                  <th>Giriş</th>
                  <th>Çıkış</th>
                  <th>Güven</th>
                  <th>Ücret</th>
                  <th>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {currentRows.map((r) => (
                  <tr key={r.id}>
                    <td style={{ fontWeight: "600", color: "var(--color-primary)" }}>{r.id}</td>
                    <td style={{ fontWeight: "600", letterSpacing: "1px", fontFamily: "monospace" }}>{r.plate_number || "-"}</td>
                    <td>{r.entry_time?.replace("T", " ").slice(0, 19) || "-"}</td>
                    <td>
                      {r.exit_time ? (
                        r.exit_time.replace("T", " ").slice(0, 19)
                      ) : (
                        <span className="pill status-in">İçeride</span>
                      )}
                    </td>
                    <td>
                      {typeof r.confidence === "number" ? (
                        <span style={{ 
                          fontWeight: "600",
                          color: r.confidence >= 0.8 ? "var(--color-success)" : r.confidence >= 0.6 ? "var(--color-warning)" : "var(--color-danger)"
                        }}>
                          {(r.confidence * 100).toFixed(1)}%
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td style={{ fontWeight: "600", color: "var(--color-primary)" }}>
                      {r.fee?.toFixed?.(2) ?? "0.00"} ₺
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                        <button
                          onClick={() => handleEditPlate(r)}
                          className="btn-small"
                          style={{ background: "var(--color-info)" }}
                        >
                          Düzenle
                        </button>
                        {!r.exit_time && (
                          <button
                            onClick={() => handleComplete(r.id)}
                            disabled={completing.has(r.id)}
                            className="btn-small"
                            style={{ background: "var(--color-success)" }}
                          >
                            {completing.has(r.id) ? (
                              <>
                                <span className="loading-spinner"></span>
                                Çıkış...
                              </>
                            ) : (
                              "Çıkış"
                            )}
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="btn-small"
                          style={{ background: "var(--color-danger)" }}
                        >
                          Sil
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "8px",
              marginTop: "24px",
              paddingTop: "24px",
              borderTop: "1px solid var(--color-border)",
              flexWrap: "wrap"
            }}>
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="btn-small"
                style={{
                  background: currentPage === 1 ? "var(--color-text-muted)" : "var(--color-primary)",
                  minWidth: "80px"
                }}
              >
                Önceki
              </button>
              
              <div style={{
                display: "flex",
                gap: "4px",
                alignItems: "center",
                flexWrap: "wrap"
              }}>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                  // İlk sayfa, son sayfa, mevcut sayfa ve yakınındaki sayfaları göster
                  if (
                    page === 1 ||
                    page === totalPages ||
                    (page >= currentPage - 1 && page <= currentPage + 1)
                  ) {
                    return (
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className="btn-small"
                        style={{
                          background: page === currentPage ? "var(--color-primary-dark)" : "var(--color-primary)",
                          minWidth: "40px",
                          fontWeight: page === currentPage ? "700" : "500"
                        }}
                      >
                        {page}
                      </button>
                    );
                  } else if (
                    page === currentPage - 2 ||
                    page === currentPage + 2
                  ) {
                    return (
                      <span key={page} style={{ padding: "0 4px", color: "var(--color-text-muted)" }}>
                        ...
                      </span>
                    );
                  }
                  return null;
                })}
              </div>
              
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="btn-small"
                style={{
                  background: currentPage === totalPages ? "var(--color-text-muted)" : "var(--color-primary)",
                  minWidth: "80px"
                }}
              >
                Sonraki
              </button>
              
              <span style={{
                color: "var(--color-text-secondary)",
                fontSize: "0.875rem",
                marginLeft: "12px"
              }}>
                Sayfa {currentPage} / {totalPages}
              </span>
            </div>
          )}
        </>
      )}
      {error && <div className="error-message" style={{ marginTop: "20px" }}>{error}</div>}
    </div>
  );
}
