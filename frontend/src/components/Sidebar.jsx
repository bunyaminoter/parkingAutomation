import React, { useState } from "react";
import "./Sidebar.css";

export default function Sidebar({ 
  items = [], 
  onItemClick, 
  activeItem = null,
  cameraStatus = null, // { active: boolean, autoDetect: boolean }
  userInfo = null
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleItemClick = (item) => {
    if (item.onClick) {
      item.onClick();
    } else if (onItemClick) {
      onItemClick(item);
    }
  };

  return (
    <aside className={`sidebar ${isCollapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        {!isCollapsed && (
          <div className="sidebar-brand">
            <div className="brand-icon">🚗</div>
            <div className="brand-text">
              <h3>La Parque</h3>
              <p>Otopark Yönetimi</p>
            </div>
          </div>
        )}
        <button 
          className="sidebar-toggle"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? "Sidebar'ı genişlet" : "Sidebar'ı daralt"}
        >
          {isCollapsed ? "→" : "←"}
        </button>
      </div>

      {userInfo && !isCollapsed && (
        <div className="sidebar-user-info">
          <div className="user-avatar">
            {userInfo.email?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="user-details">
            <div className="user-name">{userInfo.email || "Kullanıcı"}</div>
            <div className="user-role">{userInfo.role || ""}</div>
          </div>
        </div>
      )}

      {cameraStatus && !isCollapsed && (
        <div className="sidebar-camera-status">
          <div className="camera-status-header">
            <span className="camera-icon">📷</span>
            <span className="camera-label">Kamera Durumu</span>
          </div>
          <div className="camera-status-indicator">
            <div className={`status-dot ${cameraStatus.active ? "active" : "inactive"}`}></div>
            <span className="status-text">
              {cameraStatus.active ? "Aktif" : "Pasif"}
            </span>
          </div>
          {cameraStatus.active && cameraStatus.autoDetect && (
            <div className="auto-detect-badge">
              <span className="badge-icon">⚡</span>
              <span>Sürekli Algılama</span>
            </div>
          )}
        </div>
      )}

      <nav className="sidebar-nav">
        <div className="nav-section">
          {!isCollapsed && (
            <div className="nav-section-title">İşlemler</div>
          )}
          <ul className="nav-list">
            {items.map((item, index) => {
              const isActive = activeItem === item.id || activeItem === item.key;
              return (
                <li key={item.id || item.key || index}>
                  <button
                    className={`nav-item ${isActive ? "active" : ""} ${item.danger ? "danger" : ""}`}
                    onClick={() => handleItemClick(item)}
                    disabled={item.disabled}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <span className="nav-icon">{item.icon || "•"}</span>
                    {!isCollapsed && (
                      <span className="nav-label">{item.label}</span>
                    )}
                    {item.badge && !isCollapsed && (
                      <span className="nav-badge">{item.badge}</span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </nav>

      {!isCollapsed && (
        <div className="sidebar-footer">
          <div className="sidebar-footer-text">
            <p>© 2025 La Parque</p>
            <p className="footer-version">v1.0.0</p>
          </div>
        </div>
      )}
    </aside>
  );
}

