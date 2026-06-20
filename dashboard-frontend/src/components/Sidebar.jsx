// src/components/Sidebar.jsx
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Navigation items — easy to extend later
const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊", exact: true },
  { to: "/dashboard/orders", label: "Orders", icon: "📋" },
  { to: "/dashboard/masters", label: "Masters", icon: "👷" },
  { to: "/dashboard/clients", label: "Clients", icon: "👥" },
  { to: "/dashboard/finance", label: "Finance", icon: "💰" },
  { to: "/dashboard/analytics", label: "Analytics", icon: "📈" },
  { to: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export default function Sidebar() {
  const { user } = useAuth();

  return (
    <aside style={styles.sidebar}>
      {/* Brand */}
      <div style={styles.brand}>
        <div style={styles.logoMark}>iT</div>
        <div>
          <div style={styles.brandName}>InTask</div>
          <div style={styles.brandSub}>Operator</div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navItem,
              ...(isActive ? styles.navItemActive : {}),
            })}
          >
            <span style={styles.navIcon}>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom: user info */}
      <div style={styles.userBox}>
        <div style={styles.userAvatar}>
          {user?.phone?.slice(-2) || "?"}
        </div>
        <div style={{ overflow: "hidden" }}>
          <div style={styles.userPhone}>{user?.phone || "—"}</div>
          <div style={styles.userRole}>{user?.role || "—"}</div>
        </div>
      </div>
    </aside>
  );
}

// ===== Inline styles =====
const styles = {
  sidebar: {
    width: 220,
    minHeight: "100vh",
    background: "var(--sidebar-bg)",
    color: "#fff",
    display: "flex",
    flexDirection: "column",
    padding: "18px 0",
    boxSizing: "border-box",
    position: "sticky",
    top: 0,
    flexShrink: 0,
    fontFamily: "system-ui, sans-serif",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "0 18px 18px",
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    marginBottom: 14,
  },
  logoMark: {
    width: 32,
    height: 32,
    background: "#2A8A8A",
    color: "#fff",
    borderRadius: 7,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 14,
    flexShrink: 0,
  },
  brandName: {
    fontSize: 15,
    fontWeight: 600,
    color: "#fff",
    lineHeight: 1.2,
  },
  brandSub: {
    fontSize: 11,
    color: "rgba(255,255,255,0.5)",
    lineHeight: 1.2,
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    padding: "0 10px",
    flex: 1,
  },
  navItem: {
    display: "flex",
    alignItems: "center",
    gap: 11,
    padding: "9px 11px",
    borderRadius: 7,
    color: "rgba(255,255,255,0.72)",
    fontSize: 13.5,
    textDecoration: "none",
    transition: "background 0.12s, color 0.12s",
  },
  navItemActive: {
    background: "#2A8A8A",
    color: "#fff",
    fontWeight: 500,
  },
  navIcon: {
    fontSize: 15,
    width: 18,
    textAlign: "center",
  },
  userBox: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    margin: "14px 14px 0",
    padding: "12px",
    background: "rgba(255,255,255,0.04)",
    borderRadius: 8,
  },
  userAvatar: {
    width: 32,
    height: 32,
    background: "#C9A961",
    color: "#1A2B4A",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 12,
    flexShrink: 0,
  },
  userPhone: {
    fontSize: 12,
    color: "#fff",
    fontWeight: 500,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  userRole: {
    fontSize: 10,
    color: "rgba(255,255,255,0.5)",
    textTransform: "capitalize",
  },
};