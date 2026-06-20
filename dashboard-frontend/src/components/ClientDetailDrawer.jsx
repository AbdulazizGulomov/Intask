// src/components/ClientDetailDrawer.jsx
import { useEffect, useState } from "react";
import { fetchClientDetail, fetchOrders } from "../api/dashboard";

const STATUS_STYLES = {
  scheduled: { bg: "rgba(201,169,97,0.16)", color: "#C9A961", label: "Scheduled" },
  in_progress: { bg: "rgba(42,138,138,0.16)", color: "#2A8A8A", label: "In Progress" },
  completed: { bg: "rgba(26,43,74,0.12)", color: "#1A2B4A", label: "Completed" },
  cancelled: { bg: "rgba(136,136,136,0.18)", color: "#666", label: "Cancelled" },
  disputed: { bg: "rgba(216,90,48,0.16)", color: "#D85A30", label: "Disputed" },
};

export default function ClientDetailDrawer({ clientId, onClose }) {
  const [client, setClient] = useState(null);
  const [recentOrders, setRecentOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load client + their orders
  useEffect(() => {
    if (!clientId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setClient(null);
    setRecentOrders([]);

    fetchClientDetail(clientId)
      .then((data) => {
        if (cancelled) return;
        setClient(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load client");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [clientId]);

  // Fetch orders for this client once we have their phone
  useEffect(() => {
    if (!client?.phone) return;
    let cancelled = false;

    fetchOrders({ search: client.phone, page: 1 })
      .then((data) => {
        if (cancelled) return;
        // Filter strictly to this employer (search may match other fields)
        const filtered = (data.results || []).filter(
          (o) => o.employer_phone === client.phone
        );
        setRecentOrders(filtered.slice(0, 5));
      })
      .catch((err) => {
        console.warn("Could not load recent orders:", err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [client]);

  // Close on Esc
  useEffect(() => {
    function handleEsc(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  if (!clientId) return null;

  function formatMoney(amount) {
    if (!amount) return "0 UZS";
    return `${Number(amount).toLocaleString("en-US")} UZS`;
  }

  function formatDate(iso, withTime = true) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      ...(withTime && { hour: "2-digit", minute: "2-digit" }),
    });
  }

  function formatRelative(iso) {
    if (!iso) return "Never ordered";
    const d = new Date(iso);
    const now = new Date();
    const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  }

  function StatusBadge({ status }) {
    const s = STATUS_STYLES[status] || { bg: "var(--border-subtle)", color: "var(--text-muted)", label: status };
    return (
      <span
        style={{
          background: s.bg,
          color: s.color,
          padding: "2px 8px",
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 500,
        }}
      >
        {s.label}
      </span>
    );
  }

  // Cancellation color
  function getCancellationStyle(rate) {
    if (rate === 0) return { color: "#2A8A8A" };
    if (rate < 20) return { color: "var(--text)" };
    if (rate < 40) return { color: "#C9A961" };
    return { color: "#D85A30" };
  }

  const isVIP = client?.total_spent >= 5_000_000;

  return (
    <>
      <div style={styles.backdrop} onClick={onClose} />

      <aside style={styles.drawer}>
        <div style={styles.header}>
          <div>
            <div style={styles.headerLabel}>Client profile</div>
            <h2 style={styles.headerTitle}>
              {loading ? "Loading…" : client ? `#${client.id}` : "Error"}
            </h2>
          </div>
          <button style={styles.closeBtn} onClick={onClose} title="Close (Esc)">
            ✕
          </button>
        </div>

        <div style={styles.content}>
          {loading && <div style={styles.loading}>Loading client profile…</div>}

          {error && <div style={styles.errorBox}>Failed to load: {error}</div>}

          {client && !loading && (
            <>
              {/* Hero */}
              <div style={styles.hero}>
                <div style={styles.bigAvatarWrap}>
                  <div
                    style={{
                      ...styles.heroStatusDot,
                      background: client.is_active ? "#2A8A8A" : "var(--text-faint-2)",
                    }}
                  />
                  <div style={styles.bigAvatar}>
                    {(client.full_name || client.phone || "?")
                      .charAt(0)
                      .toUpperCase()}
                  </div>
                </div>
                <h3 style={styles.heroName}>
                  {client.full_name?.trim() || client.username || "Unnamed client"}
                  {isVIP && <span style={styles.vipBadge}>VIP</span>}
                </h3>
                <div style={styles.heroPhone}>{client.phone || "—"}</div>
                <div style={styles.heroStatus}>
                  {client.is_active ? "🟢 Active client" : "⚪ Inactive"} ·{" "}
                  Joined {formatDate(client.created_at, false)}
                </div>
              </div>

              {/* Stat cards */}
              <div style={styles.statsGrid}>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>{client.total_orders || 0}</div>
                  <div style={styles.statLabel}>Total orders</div>
                </div>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>{client.completed_orders || 0}</div>
                  <div style={styles.statLabel}>Completed</div>
                </div>
                <div style={styles.statCard}>
                  <div
                    style={{
                      ...styles.statNumber,
                      ...getCancellationStyle(client.cancellation_rate),
                    }}
                  >
                    {client.cancellation_rate || 0}%
                  </div>
                  <div style={styles.statLabel}>Cancelled</div>
                </div>
              </div>

              {/* Money */}
              <div style={styles.moneyCard}>
                <div style={styles.moneyLabel}>Total spent (lifetime)</div>
                <div style={styles.moneyValue}>
                  {formatMoney(client.total_spent)}
                </div>
              </div>

              {/* Account info */}
              <Section title="Account">
                <InfoRow label="ID" value={`#${client.id}`} />
                <InfoRow label="Phone" value={client.phone || "—"} />
                <InfoRow label="Username" value={client.username || "—"} />
                <InfoRow
                  label="Status"
                  value={client.is_active ? "Active" : "Inactive"}
                />
                <InfoRow label="Joined" value={formatDate(client.created_at)} />
                <InfoRow
                  label="Last order"
                  value={formatRelative(client.last_order_at)}
                />
              </Section>

              {/* Recent orders */}
              <Section
                title={`Recent orders${recentOrders.length ? ` (${recentOrders.length})` : ""}`}
              >
                {recentOrders.length === 0 ? (
                  <div style={{ color: "var(--text-faint)", fontSize: 13 }}>
                    No orders for this client.
                  </div>
                ) : (
                  <div style={styles.ordersList}>
                    {recentOrders.map((order) => (
                      <div key={order.id} style={styles.orderRow}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={styles.orderTitle}>
                            #{order.id} · {order.title || "Untitled"}
                          </div>
                          <div style={styles.orderMeta}>
                            {formatDate(order.created_at, false)} ·{" "}
                            {order.agreed_price
                              ? `${Number(order.agreed_price).toLocaleString()} UZS`
                              : "—"}
                          </div>
                        </div>
                        <StatusBadge status={order.status} />
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            </>
          )}
        </div>
      </aside>
    </>
  );
}

function Section({ title, children }) {
  return (
    <div style={styles.section}>
      <h4 style={styles.sectionTitle}>{title}</h4>
      <div>{children}</div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div style={styles.infoRow}>
      <div style={styles.infoLabel}>{label}</div>
      <div style={styles.infoValue}>{value}</div>
    </div>
  );
}

const styles = {
  backdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(26,43,74,0.4)",
    zIndex: 50,
    fontFamily: "system-ui, sans-serif",
  },
  drawer: {
    position: "fixed",
    top: 0,
    right: 0,
    width: 440,
    maxWidth: "90vw",
    height: "100vh",
    background: "var(--card)",
    boxShadow: "-8px 0 32px rgba(0,0,0,0.15)",
    zIndex: 51,
    display: "flex",
    flexDirection: "column",
    fontFamily: "system-ui, sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    padding: "20px 22px",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  },
  headerLabel: {
    fontSize: 11,
    color: "var(--text-faint)",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  headerTitle: {
    margin: 0,
    fontSize: 22,
    fontWeight: 600,
    color: "var(--text)",
  },
  closeBtn: {
    width: 32,
    height: 32,
    border: "1px solid var(--border)",
    background: "var(--card)",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
    color: "var(--text-muted)",
  },
  content: {
    flex: 1,
    overflowY: "auto",
    padding: "20px 22px",
  },
  loading: {
    padding: "40px 0",
    textAlign: "center",
    color: "var(--text-faint)",
    fontSize: 13,
  },
  errorBox: {
    padding: "10px 14px",
    background: "rgba(216,90,48,0.08)",
    color: "#D85A30",
    borderRadius: 8,
    fontSize: 13,
    border: "1px solid rgba(216,90,48,0.2)",
  },
  hero: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    paddingBottom: 18,
    borderBottom: "1px solid var(--border-subtle)",
    marginBottom: 16,
  },
  bigAvatarWrap: {
    position: "relative",
    marginBottom: 12,
  },
  bigAvatar: {
    width: 80,
    height: 80,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A8A8A 0%, #1A2B4A 100%)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 28,
  },
  heroStatusDot: {
    position: "absolute",
    bottom: 2,
    right: 2,
    width: 18,
    height: 18,
    borderRadius: "50%",
    border: "3px solid #fff",
    zIndex: 1,
  },
  heroName: {
    margin: 0,
    fontSize: 18,
    fontWeight: 600,
    color: "var(--text)",
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  vipBadge: {
    background: "#C9A961",
    color: "#fff",
    padding: "2px 8px",
    borderRadius: 5,
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 0.5,
  },
  heroPhone: {
    fontSize: 13,
    color: "#2A8A8A",
    fontWeight: 500,
    marginTop: 4,
    fontFamily: "monospace",
  },
  heroStatus: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 8,
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 8,
    marginBottom: 14,
  },
  statCard: {
    background: "var(--surface-2)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: "12px 8px",
    textAlign: "center",
  },
  statNumber: {
    fontSize: 18,
    fontWeight: 600,
    color: "var(--text)",
  },
  statLabel: {
    fontSize: 10,
    color: "var(--text-faint)",
    textTransform: "uppercase",
    letterSpacing: 0.4,
    marginTop: 2,
  },
  moneyCard: {
    background: "linear-gradient(135deg, #1A2B4A 0%, #2A8A8A 100%)",
    color: "#fff",
    borderRadius: 10,
    padding: "16px 18px",
    marginBottom: 16,
  },
  moneyLabel: {
    fontSize: 11,
    opacity: 0.8,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  moneyValue: {
    fontSize: 20,
    fontWeight: 600,
  },
  section: {
    paddingTop: 16,
    paddingBottom: 4,
    borderTop: "1px solid var(--border-subtle)",
    marginBottom: 8,
  },
  sectionTitle: {
    margin: "0 0 10px",
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-faint)",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  infoRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "6px 0",
  },
  infoLabel: {
    fontSize: 12,
    color: "var(--text-faint)",
  },
  infoValue: {
    fontSize: 13,
    color: "var(--text)",
    fontWeight: 500,
  },
  ordersList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  orderRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    padding: "10px 12px",
    background: "var(--surface-2)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 8,
  },
  orderTitle: {
    fontSize: 12,
    color: "var(--text)",
    fontWeight: 500,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  orderMeta: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 2,
  },
};