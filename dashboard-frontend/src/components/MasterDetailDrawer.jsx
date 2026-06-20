// src/components/MasterDetailDrawer.jsx
import { useEffect, useState } from "react";
import { fetchMasterDetail, fetchOrders } from "../api/dashboard";

const STATUS_STYLES = {
  scheduled: { bg: "rgba(201,169,97,0.16)", color: "#C9A961", label: "Scheduled" },
  in_progress: { bg: "rgba(42,138,138,0.16)", color: "#2A8A8A", label: "In Progress" },
  completed: { bg: "rgba(26,43,74,0.12)", color: "#1A2B4A", label: "Completed" },
  cancelled: { bg: "rgba(136,136,136,0.18)", color: "#666", label: "Cancelled" },
  disputed: { bg: "rgba(216,90,48,0.16)", color: "#D85A30", label: "Disputed" },
};

export default function MasterDetailDrawer({ masterId, onClose }) {
  const [master, setMaster] = useState(null);
  const [recentOrders, setRecentOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!masterId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setMaster(null);
    setRecentOrders([]);

    // Fetch master profile + their recent orders in parallel
    fetchMasterDetail(masterId)
      .then((data) => {
        if (cancelled) return;
        setMaster(data);

        // Now fetch the orders for this worker
        // Note: backend doesn't have a worker filter param yet, so we
        // fetch the first page of orders and filter client-side.
        return fetchOrders({ page: 1 });
      })
      .then((ordersData) => {
        if (cancelled || !ordersData) return;
        const all = ordersData.results || [];
        // Filter to this worker's phone
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load master");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [masterId]);

  // Separate effect to fetch orders for this master once we know their user_id
  useEffect(() => {
    if (!master?.user_id) return;
    let cancelled = false;

    // Search by phone gets the worker's orders most reliably
    fetchOrders({ search: master.phone, page: 1 })
      .then((data) => {
        if (cancelled) return;
        // Filter strictly to this worker (search may return other matches)
        const filtered = (data.results || []).filter(
          (o) => o.worker_phone === master.phone
        );
        setRecentOrders(filtered.slice(0, 5));
      })
      .catch((err) => {
        console.warn("Could not load recent orders:", err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [master]);

  // Close on Esc
  useEffect(() => {
    function handleEsc(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  if (!masterId) return null;

  function getInitials(m) {
    const first = (m.first_name || "").trim();
    const last = (m.last_name || "").trim();
    if (first && last) return `${first[0]}${last[0]}`.toUpperCase();
    if (first) return first.slice(0, 2).toUpperCase();
    if (m.phone) return m.phone.slice(-2);
    return "??";
  }

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function formatPrice(price, currency = "UZS") {
    if (!price) return "—";
    return `${Number(price).toLocaleString("en-US")} ${currency}`;
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

  return (
    <>
      <div style={styles.backdrop} onClick={onClose} />

      <aside style={styles.drawer}>
        <div style={styles.header}>
          <div>
            <div style={styles.headerLabel}>Master profile</div>
            <h2 style={styles.headerTitle}>
              {loading ? "Loading…" : master ? `#${master.id}` : "Error"}
            </h2>
          </div>
          <button style={styles.closeBtn} onClick={onClose} title="Close (Esc)">
            ✕
          </button>
        </div>

        <div style={styles.content}>
          {loading && <div style={styles.loading}>Loading master profile…</div>}

          {error && <div style={styles.errorBox}>Failed to load: {error}</div>}

          {master && !loading && (
            <>
              {/* Big avatar + name */}
              <div style={styles.profileHero}>
                <div style={styles.bigAvatarWrap}>
                  <div
                    style={{
                      ...styles.heroStatusDot,
                      background: master.is_active ? "#2A8A8A" : "var(--text-faint-2)",
                    }}
                  />
                  <div style={styles.bigAvatar}>{getInitials(master)}</div>
                </div>
                <h3 style={styles.heroName}>
                  {master.full_name?.trim() || master.phone || "Unknown"}
                </h3>
                <div style={styles.heroProfession}>
                  {master.profession_name || "No profession set"}
                </div>
                <div style={styles.heroStatus}>
                  {master.is_active ? "🟢 Active" : "⚪ Inactive"} ·{" "}
                  {master.is_completed ? "Profile complete" : "Profile incomplete"}
                </div>
              </div>

              {/* Stats — rating, orders, age */}
              <div style={styles.statsGrid}>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>
                    {master.avg_rating != null
                      ? Math.round(master.avg_rating * 10) / 10
                      : "—"}
                  </div>
                  <div style={styles.statLabel}>
                    <span style={{ color: "#C9A961" }}>★</span> Rating
                  </div>
                </div>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>
                    {master.completed_orders || 0}
                  </div>
                  <div style={styles.statLabel}>Completed</div>
                </div>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>{master.age || "—"}</div>
                  <div style={styles.statLabel}>Age</div>
                </div>
              </div>

              {/* Personal details */}
              <Section title="Personal info">
                <InfoRow label="First name" value={master.first_name || "—"} />
                <InfoRow label="Last name" value={master.last_name || "—"} />
                <InfoRow label="Phone" value={master.phone || "—"} />
                <InfoRow
                  label="Gender"
                  value={
                    master.gender === "male"
                      ? "Male"
                      : master.gender === "female"
                        ? "Female"
                        : "—"
                  }
                />
                <InfoRow label="Joined" value={formatDate(master.created_at)} />
              </Section>

              {/* Recent orders */}
              <Section title={`Recent orders${recentOrders.length ? ` (${recentOrders.length})` : ""}`}>
                {recentOrders.length === 0 ? (
                  <div style={{ color: "var(--text-faint)", fontSize: 13 }}>
                    No orders yet for this worker.
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
                            {formatDate(order.created_at)} ·{" "}
                            {formatPrice(order.agreed_price, order.currency)}
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
  profileHero: {
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
  },
  heroProfession: {
    fontSize: 13,
    color: "#2A8A8A",
    fontWeight: 500,
    marginTop: 4,
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
    marginBottom: 16,
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