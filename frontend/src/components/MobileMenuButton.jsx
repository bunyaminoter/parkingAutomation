import React from "react";
import "./Sidebar.css";

export default function MobileMenuButton({ onClick, isOpen }) {
  return (
    <button
      className="mobile-menu-button"
      onClick={onClick}
      aria-label={isOpen ? "Menüyü kapat" : "Menüyü aç"}
    >
      {isOpen ? "✕" : "☰"}
    </button>
  );
}

