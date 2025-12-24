import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./components/LoginPage";
import AdminPage from "./components/AdminPage";
import UserPage from "./components/UserPage";
import SuperAdminPage from "./components/SuperAdminPage";
import SuperAdminLoginPage from "./components/SuperAdminLoginPage";
import ResetPasswordPage from "./components/ResetPasswordPage";
import UpdateUserInfoPage from "./components/UpdateUserInfoPage";
import "./App.css";

export default function App() {
  return (
    <Router future={{ v7_startTransition: true }}>
      <div className="app">
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/user" element={<UserPage />} />
          {/* Üst admin login ve dashboardu */}
          <Route path="/panel-login" element={<SuperAdminLoginPage />} />
          <Route path="/panel" element={<SuperAdminPage />} />
          {/* Şifre sıfırlama ve kullanıcı bilgileri güncelleme */}
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/update-user-info" element={<UpdateUserInfoPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}