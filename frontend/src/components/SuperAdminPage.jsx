import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import { fetchJSON } from "../utils";
import "../App.css";

export default function SuperAdminPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
   const [creating, setCreating] = useState(false);
   const [newUsername, setNewUsername] = useState("");
   const [newPassword, setNewPassword] = useState("");
   const [newIsSuper, setNewIsSuper] = useState(false);
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
          // Üst admin değilse giriş izni verme
          navigate("/");
        }
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
    if (!newUsername.trim() || !newPassword.trim()) return;
    try {
      setCreating(true);
      await fetchJSON(API.base + API.createUser, {
        method: "POST",
        credentials: "include",
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword.trim(),
          is_super_admin: newIsSuper ? 1 : 0,
        }),
      });
      setNewUsername("");
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
      `Kullanıcı için yeni şifreyi girin: ${user.username}`
    );
    if (!pwd || pwd.trim() === "") return;
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
    const username = window.prompt(
      "Yeni kullanıcı adını girin (boş bırakılırsa değişmez):",
      user.username
    );
    if (username === null) return;

    const makeSuper = window.confirm(
      "Bu kullanıcı ÜST ADMIN olsun mu? OK = EVET, İptal = HAYIR"
    );

    const payload = {};
    if (username.trim() && username.trim() !== user.username) {
      payload.username = username.trim();
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
    if (!window.confirm(`Kullanıcı silinsin mi? (${user.username})`)) return;
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

  return (
    <div className="container">
      <div className="admin-header">
        <h1>Üst Admin Paneli</h1>
        <button onClick={handleLogout} className="logout-btn">
          Çıkış Yap
        </button>
      </div>

      <div className="card">
        <h2>Kullanıcılar</h2>

        <form
          onSubmit={handleCreateUser}
          style={{
            display: "flex",
            gap: "8px",
            alignItems: "flex-end",
            marginBottom: "16px",
            flexWrap: "wrap",
          }}
        >
          <div className="form-group">
            <label>Yeni Kullanıcı Adı</label>
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              disabled={creating}
            />
          </div>
          <div className="form-group">
            <label>Şifre</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={creating}
            />
          </div>
          <div className="form-group" style={{ display: "flex", alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <input
                type="checkbox"
                checked={newIsSuper}
                onChange={(e) => setNewIsSuper(e.target.checked)}
                disabled={creating}
              />
              Üst admin
            </label>
          </div>
          <button
            type="submit"
            disabled={creating || !newUsername.trim() || !newPassword.trim()}
            className="btn-small"
          >
            {creating ? "Ekleniyor..." : "Yeni Kullanıcı Ekle"}
          </button>
        </form>
        {loading ? (
          <p className="muted">Yükleniyor...</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Kullanıcı Adı</th>
                <th>Rol</th>
                <th>Oluşturulma</th>
                <th>İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.username}</td>
                  <td>{u.is_super_admin === 1 ? "Üst Admin" : "Admin"}</td>
                  <td>
                    {u.created_at
                      ? u.created_at.replace("T", " ").slice(0, 19)
                      : "-"}
                  </td>
                  <td>
                    <button
                      className="btn-small"
                      onClick={() => handleEditUser(u)}
                      disabled={updatingId === u.id}
                      style={{ marginRight: "4px" }}
                    >
                      Düzenle
                    </button>
                    <button
                      className="btn-small"
                      onClick={() => handleChangePassword(u)}
                      disabled={updatingId === u.id}
                      style={{ marginRight: "4px" }}
                    >
                      Şifre
                    </button>
                    <button
                      className="btn-small"
                      onClick={() => handleDeleteUser(u)}
                      disabled={updatingId === u.id}
                      style={{ backgroundColor: "#dc3545", color: "#fff" }}
                    >
                      Sil
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {error && <p className="muted">{error}</p>}
      </div>
    </div>
  );
}


