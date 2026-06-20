// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import DashboardLayout from "./components/DashboardLayout";

import LoginPage from "./pages/LoginPage";
import DashboardHome from "./pages/DashboardHome";
import OrdersPage from "./pages/OrdersPage";
import MastersPage from "./pages/MastersPage";
import ClientsPage from "./pages/ClientsPage";
import FinancePage from "./pages/FinancePage";
import AnalyticsPage from "./pages/AnalyticsPage";
import SettingsPage from "./pages/SettingsPage";

function ComingSoonPage({ title }) {
  return (
    <div>
      <h2 style={{ color: "var(--text)", margin: 0 }}>{title}</h2>
      <p style={{ color: "var(--text-faint)", marginTop: 8 }}>
        This page is coming in a future phase.
      </p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter basename="/dashboard">
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requireRole={["operator", "admin"]}>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardHome />} />
            <Route path="orders" element={<OrdersPage />} />
            <Route path="masters" element={<MastersPage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route path="finance" element={<FinancePage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route
            path="*"
            element={
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100vh",
                  color: "var(--text-faint)",
                  fontFamily: "system-ui, sans-serif",
                }}
              >
                <h1 style={{ color: "var(--text)", margin: 0 }}>404</h1>
                <p>Page not found</p>
              </div>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}