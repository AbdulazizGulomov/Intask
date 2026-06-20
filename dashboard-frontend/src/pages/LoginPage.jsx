// src/pages/LoginPage.jsx
import { useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // If already logged in, send them straight to dashboard
  if (!authLoading && isAuthenticated) {
    const redirectTo = location.state?.from?.pathname || "/dashboard";
    return <Navigate to={redirectTo} replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    // Quick client-side validation
    if (!phone.trim() || !password.trim()) {
      setError("Phone and password are required");
      return;
    }

    setSubmitting(true);
    try {
      await login(phone.trim(), password);
      // After successful login, go to wherever they tried to reach (or dashboard)
      const redirectTo = location.state?.from?.pathname || "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      // Pull error message from DRF response if present
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        "Invalid phone or password";
      setError(typeof detail === "string" ? detail : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Logo / Brand */}
        <div style={styles.brand}>
          <div style={styles.logoMark}>iT</div>
          <div>
            <div style={styles.brandName}>InTask</div>
            <div style={styles.brandSub}>Operator Dashboard</div>
          </div>
        </div>

        <h1 style={styles.heading}>Welcome back</h1>
        <p style={styles.subtitle}>Sign in with your operator credentials</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          {/* Phone field */}
          <label style={styles.label}>
            <span style={styles.labelText}>Phone</span>
            <input
              type="tel"
              autoComplete="username"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+998 90 123 45 67"
              style={styles.input}
              disabled={submitting}
              autoFocus
            />
          </label>

          {/* Password field */}
          <label style={styles.label}>
            <span style={styles.labelText}>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={styles.input}
              disabled={submitting}
            />
          </label>

          {/* Error message */}
          {error && <div style={styles.errorBox}>{error}</div>}

          {/* Submit button */}
          <button
            type="submit"
            disabled={submitting}
            style={{
              ...styles.button,
              opacity: submitting ? 0.7 : 1,
              cursor: submitting ? "wait" : "pointer",
            }}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div style={styles.footer}>
          InTask Operator Dashboard · v1.0
        </div>
      </div>
    </div>
  );
}

// ===== Inline styles =====
const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1A2B4A",
    backgroundImage:
      "radial-gradient(circle at 20% 30%, rgba(42,138,138,0.18) 0%, transparent 50%), radial-gradient(circle at 80% 70%, rgba(201,169,97,0.10) 0%, transparent 50%)",
    padding: "20px",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  card: {
    width: "100%",
    maxWidth: 400,
    background: "var(--card)",
    borderRadius: 12,
    padding: "32px 28px",
    boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 24,
  },
  logoMark: {
    width: 42,
    height: 42,
    background: "#2A8A8A",
    color: "#fff",
    borderRadius: 8,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 18,
  },
  brandName: {
    fontSize: 16,
    fontWeight: 600,
    color: "var(--text)",
    lineHeight: 1.2,
  },
  brandSub: {
    fontSize: 12,
    color: "var(--text-faint)",
    lineHeight: 1.2,
  },
  heading: {
    margin: "0 0 4px",
    fontSize: 22,
    fontWeight: 600,
    color: "var(--text)",
  },
  subtitle: {
    margin: "0 0 24px",
    fontSize: 13,
    color: "var(--text-faint)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 14,
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  labelText: {
    fontSize: 12,
    fontWeight: 500,
    color: "var(--text)",
    letterSpacing: 0.2,
  },
  input: {
    padding: "10px 12px",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 14,
    outline: "none",
    transition: "border-color 0.15s",
    color: "var(--text)",
    background: "var(--surface-2)",
  },
  errorBox: {
    background: "rgba(216,90,48,0.08)",
    color: "#D85A30",
    padding: "8px 12px",
    borderRadius: 6,
    fontSize: 13,
    border: "1px solid rgba(216,90,48,0.2)",
  },
  button: {
    marginTop: 6,
    padding: "11px 16px",
    background: "#2A8A8A",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    transition: "background 0.15s",
  },
  footer: {
    marginTop: 24,
    paddingTop: 16,
    borderTop: "1px solid var(--border-subtle)",
    fontSize: 11,
    color: "var(--text-faint-2)",
    textAlign: "center",
  },
};