// src/auth/ProtectedRoute.jsx
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ children, requireRole = null }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  // Still verifying token on mount? Show a loading state.
  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          color: "#888",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        Loading…
      </div>
    );
  }

  // Not logged in → redirect to login, remember where they were going
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Role gate (optional)
  if (requireRole) {
    const allowedRoles = Array.isArray(requireRole) ? requireRole : [requireRole];
    const userRole = user?.role;
    const isSuperuser = user?.is_superuser;

    if (!allowedRoles.includes(userRole) && !isSuperuser) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100vh",
            gap: 12,
            fontFamily: "system-ui, sans-serif",
          }}
        >
          <h1 style={{ color: "#1A2B4A", margin: 0 }}>403</h1>
          <p style={{ color: "#666", margin: 0 }}>
            You don't have permission to access this page.
          </p>
        </div>
      );
    }
  }

  return children;
}