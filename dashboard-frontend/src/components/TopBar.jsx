// src/components/TopBar.jsx
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Match URL paths to display titles
const PAGE_TITLES = {
  "/dashboard": "Dashboard",
  "/dashboard/orders": "Orders",
  "/dashboard/masters": "Masters",
  "/dashboard/clients": "Clients",
  "/dashboard/finance": "Finance",
  "/dashboard/analytics": "Analytics",
  "/dashboard/settings": "Settings",
};

export default function TopBar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  // Lookup current page title, default to "Dashboard"
  const title = PAGE_TITLES[location.pathname] || "Dashboard";

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header style={styles.topbar}>
      {/* Left: page title + breadcrumb-style subtitle */}
      <div>
        <h1 style={styles.title}>{title}</h1>
        <div style={styles.subtitle}>InTask Operator Panel</div>
      </div>

      {/* Right: user menu */}
      <div style={styles.right}>
        {/* Notifications bell (visual only for now) */}
        <button style={styles.iconBtn} title="Notifications">
          🔔
        </button>

        {/* User pill — click to open menu */}
        <div style={{ position: "relative" }}>
          <button
            style={styles.userPill}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span style={styles.userAvatar}>{user?.phone?.slice(-2) || "?"}</span>
            <span style={styles.userPhone}>{user?.phone}</span>
            <span style={styles.chevron}>▾</span>
          </button>

          {/* Dropdown menu */}
          {menuOpen && (
            <>
              {/* Click-outside backdrop */}
              <div
                style={styles.backdrop}
                onClick={() => setMenuOpen(false)}
              />
              <div style={styles.dropdown}>
                <div style={styles.dropdownHeader}>
                  <div style={styles.dropdownPhone}>{user?.phone}</div>
                  <div style={styles.dropdownRole}>{user?.role}</div>
                </div>
                <button
                  style={styles.dropdownItem}
                  onClick={handleLogout}
                >
                  <span style={{ marginRight: 8 }}>⎋</span> Logout
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

// ===== Inline styles =====
const styles = {
  topbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 24px",
    background: "var(--card)",
    borderBottom: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  title: {
    margin: 0,
    fontSize: 18,
    fontWeight: 600,
    color: "var(--text)",
    lineHeight: 1.2,
  },
  subtitle: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 2,
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  iconBtn: {
    width: 36,
    height: 36,
    border: "1px solid var(--border)",
    background: "var(--card)",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  userPill: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 10px 4px 4px",
    background: "var(--surface-2)",
    border: "1px solid var(--border)",
    borderRadius: 24,
    cursor: "pointer",
    fontSize: 13,
    color: "var(--text)",
  },
  userAvatar: {
    width: 28,
    height: 28,
    background: "#2A8A8A",
    color: "#fff",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 11,
  },
  userPhone: {
    fontWeight: 500,
  },
  chevron: {
    color: "var(--text-faint)",
    fontSize: 11,
  },
  backdrop: {
    position: "fixed",
    inset: 0,
    zIndex: 5,
  },
  dropdown: {
    position: "absolute",
    top: "calc(100% + 6px)",
    right: 0,
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    boxShadow: "0 10px 30px var(--shadow)",
    minWidth: 200,
    zIndex: 10,
    overflow: "hidden",
  },
  dropdownHeader: {
    padding: "12px 14px",
    borderBottom: "1px solid var(--border-subtle)",
  },
  dropdownPhone: {
    fontSize: 13,
    fontWeight: 500,
    color: "var(--text)",
  },
  dropdownRole: {
    fontSize: 11,
    color: "var(--text-faint)",
    textTransform: "capitalize",
    marginTop: 2,
  },
  dropdownItem: {
    display: "flex",
    alignItems: "center",
    width: "100%",
    padding: "10px 14px",
    background: "var(--card)",
    border: "none",
    cursor: "pointer",
    fontSize: 13,
    color: "var(--text)",
    textAlign: "left",
    transition: "background 0.12s",
  },
};