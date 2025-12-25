import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import { fetchJSON } from "../utils";
import Sidebar from "./Sidebar";
import "../App.css";

export default function SuperAdminPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsSuper, setNewIsSuper] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [activeSection, setActiveSection] = useState("user-management");
  const navigate = useNavigate();

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch(API.base + "/api/check_session", {
          method: "GET",
          credentials: "include",
        });
        if (!response.ok) {
          navigate("/panel-login");
          return;
        }
        const data = await response.json();
        if (!data?.user || data.user.is_super_admin !== 1) {
          navigate("/");
          return;
        }
        
        setUserInfo({
          email: data.user.email,
          role: "Süper Admin"
        });
      } catch {
        navigate("/panel-login");
      }
    };

    checkSession();
  }, [navigate]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await fetchJSON(API.base + API.listUsers, {
        credentials: "include",
      });
      setUsers(data);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newEmail.trim() || !newPassword.trim()) return;
    
    // Email doğrulama
    if (!newEmail.includes("@") || !newEmail.split("@")[1].includes(".")) {
      setError("Geçerli bir e-posta adresi giriniz");
      return;
    }
    
    try {
      setCreating(true);
      await fetchJSON(API.base + API.createUser, {
        method: "POST",
        credentials: "include",
        body: JSON.stringify({
          email: newEmail.trim(),
          password: newPassword.trim(),
          is_super_admin: newIsSuper ? 1 : 0,
        }),
      });
      setNewEmail("");
      setNewPassword("");
      setNewIsSuper(false);
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleChangePassword = async (user) => {
    const pwd = window.prompt(
      `Kullanıcı için yeni şifreyi girin: ${user.email}`
    );
    if (!pwd || pwd.trim() === "") return;
    if (pwd.trim().length < 6) {
      setError("Şifre en az 6 karakter olmalıdır");
      return;
    }
    try {
      setUpdatingId(user.id);
      await fetchJSON(API.base + API.changeUserPassword(user.id), {
        method: "PUT",
        credentials: "include",
        body: JSON.stringify({ password: pwd.trim() }),
      });
      alert("Şifre güncellendi.");
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleEditUser = async (user) => {
    const email = window.prompt(
      "Yeni e-posta adresini girin (boş bırakılırsa değişmez):",
      user.email
    );
    if (email === null) return;

    // Email doğrulama
    if (email.trim() && (!email.includes("@") || !email.split("@")[1].includes("."))) {
      setError("Geçerli bir e-posta adresi giriniz");
      return;
    }

    const makeSuper = window.confirm(
      "Bu kullanıcı ÜST ADMIN olsun mu? OK = EVET, İptal = HAYIR"
    );

    const payload = {};
    if (email.trim() && email.trim() !== user.email) {
      payload.email = email.trim();
    }
    payload.is_super_admin = makeSuper ? 1 : 0;

    try {
      setUpdatingId(user.id);
      await fetchJSON(API.base + API.updateUser(user.id), {
        method: "PUT",
        credentials: "include",
        body: JSON.stringify(payload),
      });
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDeleteUser = async (user) => {
    if (!window.confirm(`Kullanıcı silinsin mi? (${user.email})`)) return;
    try {
      setUpdatingId(user.id);
      await fetchJSON(API.base + API.deleteUser(user.id), {
        method: "DELETE",
        credentials: "include",
      });
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(API.base + "/api/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      // ignore
    } finally {
      navigate("/");
    }
  };

  const handleSectionChange = (sectionId) => {
    setActiveSection(sectionId);
  };

  const sidebarItems = [
    {
      id: "user-management",
      key: "user-management",
      label: "Kullanıcı Yönetimi",
      icon: "👥",
      onClick: () => handleSectionChange("user-management")
    },
    {
      id: "create-user",
      key: "create-user",
      label: "Yeni Kullanıcı Ekle",
      icon: "➕",
      onClick: () => handleSectionChange("create-user")
    },
    {
      id: "logout",
      key: "logout",
      label: "Çıkış Yap",
      icon: "🚪",
      danger: true,
      onClick: handleLogout
    }
  ];

  const renderContent = () => {
    switch (activeSection) {
      case "user-management":
        return (
          <div className="admin-section-content">
            <div className="card">
              <h2>Kullanıcı Yönetimi</h2>

              {error && <div className="error-message">{error}</div>}

              {loading ? (
                <div style={{ textAlign: "center", padding: "48px" }}>
                  <div className="loading-spinner" style={{ margin: "0 auto 16px", borderColor: "var(--color-primary) rgba(0,0,0,0.1)", borderTopColor: "var(--color-primary)" }}></div>
                  <p className="muted">Yükleniyor...</p>
                </div>
              ) : users.length === 0 ? (
                <div style={{ textAlign: "center", padding: "48px" }}>
                  <p className="muted" style={{ fontSize: "1rem" }}>Henüz kullanıcı bulunmuyor</p>
                </div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>E-posta</th>
                        <th>Rol</th>
                        <th>Oluşturulma</th>
                        <th>İşlemler</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id}>
                          <td style={{ fontWeight: "700", color: "var(--primary-color)" }}>{u.id}</td>
                          <td style={{ fontWeight: "600" }}>{u.email}</td>
                          <td>
                            <span
                              style={{
                                padding: "4px 12px",
                                borderRadius: "12px",
                                fontSize: "0.75rem",
                                fontWeight: "600",
                                textTransform: "uppercase",
                                letterSpacing: "0.05em",
                                background: u.is_super_admin === 1 
                                  ? "var(--color-primary)"
                                  : "var(--color-success)",
                                color: "white",
                              }}
                            >
                              {u.is_super_admin === 1 ? "Üst Admin" : "Admin"}
                            </span>
                          </td>
                          <td>
                            {u.created_at
                              ? u.created_at.replace("T", " ").slice(0, 19)
                              : "-"}
                          </td>
                          <td>
                            <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                              <button
                                className="btn-small"
                                onClick={() => handleEditUser(u)}
                                disabled={updatingId === u.id}
                                style={{ background: "var(--color-info)" }}
                              >
                                Düzenle
                              </button>
                              <button
                                className="btn-small"
                                onClick={() => handleChangePassword(u)}
                                disabled={updatingId === u.id}
                                style={{ background: "var(--color-warning)", color: "#000" }}
                              >
                                Şifre
                              </button>
                              <button
                                className="btn-small"
                                onClick={() => handleDeleteUser(u)}
                                disabled={updatingId === u.id}
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
              )}
            </div>
          </div>
        );
      case "create-user":
        return (
          <div className="admin-section-content">
            <div className="card">
              <h2>Yeni Kullanıcı Ekle</h2>
              {error && <div className="error-message">{error}</div>}
              <form onSubmit={handleCreateUser}>
                <div className="form-group">
                  <label htmlFor="new-email">E-posta</label>
                  <input
                    id="new-email"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    disabled={creating}
                    placeholder="ornek@email.com"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="new-password">Şifre</label>
                  <input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    disabled={creating}
                    placeholder="Şifre"
                    required
                    minLength={6}
                  />
                </div>
                <div className="form-group">
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", userSelect: "none" }}>
                    <input
                      type="checkbox"
                      checked={newIsSuper}
                      onChange={(e) => setNewIsSuper(e.target.checked)}
                      disabled={creating}
                      style={{ width: "20px", height: "20px", cursor: "pointer" }}
                    />
                    <span style={{ fontWeight: "600" }}>Üst admin olarak oluştur</span>
                  </label>
                </div>
                <button
                  type="submit"
                  disabled={creating || !newEmail.trim() || !newPassword.trim()}
                  style={{ width: "100%" }}
                >
                  {creating ? (
                    <>
                      <span className="loading-spinner"></span>
                      Ekleniyor...
                    </>
                  ) : (
                    "Yeni Kullanıcı Ekle"
                  )}
                </button>
              </form>
            </div>
          </div>
        );
      default:
        return (
          <div className="admin-section-content">
            <div className="card">
              <h2>Kullanıcı Yönetimi</h2>

              {error && <div className="error-message">{error}</div>}

              {loading ? (
                <div style={{ textAlign: "center", padding: "48px" }}>
                  <div className="loading-spinner" style={{ margin: "0 auto 16px", borderColor: "var(--color-primary) rgba(0,0,0,0.1)", borderTopColor: "var(--color-primary)" }}></div>
                  <p className="muted">Yükleniyor...</p>
                </div>
              ) : users.length === 0 ? (
                <div style={{ textAlign: "center", padding: "48px" }}>
                  <p className="muted" style={{ fontSize: "1rem" }}>Henüz kullanıcı bulunmuyor</p>
                </div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>E-posta</th>
                        <th>Rol</th>
                        <th>Oluşturulma</th>
                        <th>İşlemler</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id}>
                          <td style={{ fontWeight: "700", color: "var(--primary-color)" }}>{u.id}</td>
                          <td style={{ fontWeight: "600" }}>{u.email}</td>
                          <td>
                            <span
                              style={{
                                padding: "4px 12px",
                                borderRadius: "12px",
                                fontSize: "0.75rem",
                                fontWeight: "600",
                                textTransform: "uppercase",
                                letterSpacing: "0.05em",
                                background: u.is_super_admin === 1 
                                  ? "var(--color-primary)"
                                  : "var(--color-success)",
                                color: "white",
                              }}
                            >
                              {u.is_super_admin === 1 ? "Üst Admin" : "Admin"}
                            </span>
                          </td>
                          <td>
                            {u.created_at
                              ? u.created_at.replace("T", " ").slice(0, 19)
                              : "-"}
                          </td>
                          <td>
                            <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                              <button
                                className="btn-small"
                                onClick={() => handleEditUser(u)}
                                disabled={updatingId === u.id}
                                style={{ background: "var(--color-info)" }}
                              >
                                Düzenle
                              </button>
                              <button
                                className="btn-small"
                                onClick={() => handleChangePassword(u)}
                                disabled={updatingId === u.id}
                                style={{ background: "var(--color-warning)", color: "#000" }}
                              >
                                Şifre
                              </button>
                              <button
                                className="btn-small"
                                onClick={() => handleDeleteUser(u)}
                                disabled={updatingId === u.id}
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
              )}
            </div>
          </div>
        );
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar 
        items={sidebarItems}
        activeItem={activeSection}
        userInfo={userInfo}
      />
      <div className="main-content" style={{ flex: 1, width: "100%" }}>
        <div className="container">
          <div className="admin-header">
            <h1>Üst Admin Paneli - Parking Automation</h1>
          </div>
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
