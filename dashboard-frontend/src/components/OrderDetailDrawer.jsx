// src/components/OrderDetailDrawer.jsx
import { useEffect, useState } from "react";
import { fetchOrderDetail, updateOrder } from "../api/dashboard";

const STATUS_STYLES = {
  scheduled: { bg: "rgba(201,169,97,0.16)", color: "#C9A961", label: "Scheduled" },
  in_progress: { bg: "rgba(42,138,138,0.16)", color: "#2A8A8A", label: "In Progress" },
  completed: { bg: "rgba(26,43,74,0.12)", color: "#1A2B4A", label: "Completed" },
  cancelled: { bg: "rgba(136,136,136,0.18)", color: "#666", label: "Cancelled" },
  disputed: { bg: "rgba(216,90,48,0.16)", color: "#D85A30", label: "Disputed" },
};

// Allowed status transitions per current status
// (what buttons to show, based on what state the order is in)
const ALLOWED_ACTIONS = {
  scheduled: [
    { target: "in_progress", label: "Start work", color: "#2A8A8A" },
    { target: "cancelled", label: "Cancel", color: "#666" },
  ],
  in_progress: [
    { target: "completed", label: "Mark completed", color: "#1A2B4A" },
    { target: "disputed", label: "Mark disputed", color: "#D85A30" },
    { target: "cancelled", label: "Cancel", color: "#666" },
  ],
  completed: [
    { target: "disputed", label: "Mark disputed", color: "#D85A30" },
  ],
  cancelled: [
    { target: "scheduled", label: "Reactivate", color: "#C9A961" },
  ],
  disputed: [
    { target: "in_progress", label: "Resume", color: "#2A8A8A" },
    { target: "completed", label: "Mark resolved", color: "#1A2B4A" },
    { target: "cancelled", label: "Cancel", color: "#666" },
  ],
};

export default function OrderDetailDrawer({ orderId, onClose, onOrderChanged }) {
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Status change state
  const [changing, setChanging] = useState(false);
  const [changeError, setChangeError] = useState(null);

  useEffect(() => {
    if (!orderId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setOrder(null);
    setChangeError(null);

    fetchOrderDetail(orderId)
      .then((data) => !cancelled && setOrder(data))
      .catch((err) => !cancelled && setError(err.message || "Failed to load order"))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  useEffect(() => {
    function handleEsc(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  async function handleStatusChange(newStatus) {
    if (!order || changing) return;

    const confirmLabel =
      ALLOWED_ACTIONS[order.status]?.find((a) => a.target === newStatus)?.label ||
      "change status";

    if (!window.confirm(`Are you sure you want to ${confirmLabel.toLowerCase()}?`)) {
      return;
    }

    setChanging(true);
    setChangeError(null);

    try {
      const updated = await updateOrder(order.id, { status: newStatus });
      setOrder(updated);
      // Notify parent table to refresh
      if (onOrderChanged) onOrderChanged();
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.status?.[0] ||
        err.message ||
        "Failed to update order";
      setChangeError(typeof detail === "string" ? detail : "Update failed");
    } finally {
      setChanging(false);
    }
  }

  if (!orderId) return null;

  function formatPrice(price, currency = "UZS") {
    if (!price) return "—";
    return `${Number(price).toLocaleString("en-US")} ${currency}`;
  }

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function StatusBadge({ status }) {
    const s = STATUS_STYLES[status] || { bg: "var(--border-subtle)", color: "var(--text-muted)", label: status };
    return (
      <span
        style={{
          background: s.bg,
          color: s.color,
          padding: "4px 12px",
          borderRadius: 999,
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        {s.label}
      </span>
    );
  }

  const actions = order ? ALLOWED_ACTIONS[order.status] || [] : [];

  return (
    <>
      <div style={styles.backdrop} onClick={onClose} />

      <aside style={styles.drawer}>
        <div style={styles.header}>
          <div>
            <div style={styles.headerLabel}>Order detail</div>
            <h2 style={styles.headerTitle}>
              {loading ? "Loading…" : order ? `#${order.id}` : "Error"}
            </h2>
          </div>
          <button style={styles.closeBtn} onClick={onClose} title="Close (Esc)">
            ✕
          </button>
        </div>

        <div style={styles.content}>
          {loading && <div style={styles.loading}>Loading order details…</div>}

          {error && <div style={styles.errorBox}>Failed to load: {error}</div>}

          {order && !loading && (
            <>
              <div style={{ marginBottom: 18 }}>
                <h3 style={styles.orderTitle}>{order.title || "Untitled order"}</h3>
                <div style={{ marginTop: 8 }}>
                  <StatusBadge status={order.status} />
                </div>
              </div>

              {/* ACTIONS — the new part */}
              {actions.length > 0 && (
                <div style={styles.actionsSection}>
                  <h4 style={styles.sectionTitle}>Actions</h4>
                  <div style={styles.actionButtons}>
                    {actions.map((action) => (
                      <button
                        key={action.target}
                        onClick={() => handleStatusChange(action.target)}
                        disabled={changing}
                        style={{
                          ...styles.actionBtn,
                          background: action.color,
                          opacity: changing ? 0.5 : 1,
                          cursor: changing ? "wait" : "pointer",
                        }}
                      >
                        {changing ? "…" : action.label}
                      </button>
                    ))}
                  </div>
                  {changeError && (
                    <div style={styles.changeError}>{changeError}</div>
                  )}
                </div>
              )}

              <Section title="Details">
                <InfoRow label="Employer" value={order.employer_phone || "—"} />
                <InfoRow label="Worker" value={order.worker_phone || "—"} />
                <InfoRow
                  label="Price"
                  value={formatPrice(order.agreed_price, order.currency)}
                />
                <InfoRow label="Address" value={order.address || "—"} />
                {order.description && (
                  <InfoRow label="Description" value={order.description} multiline />
                )}
              </Section>

              <Section title="Schedule">
                <InfoRow label="Scheduled" value={formatDate(order.scheduled_at)} />
                <InfoRow label="Started" value={formatDate(order.started_at)} />
                <InfoRow label="Completed" value={formatDate(order.completed_at)} />
                <InfoRow label="Created" value={formatDate(order.created_at)} />
              </Section>

              {(order.employer_rating || order.worker_rating) && (
                <Section title="Ratings">
                  <InfoRow
                    label="Worker rating"
                    value={order.employer_rating ? `${order.employer_rating}/5 ★` : "—"}
                  />
                  <InfoRow
                    label="Employer rating"
                    value={order.worker_rating ? `${order.worker_rating}/5 ★` : "—"}
                  />
                </Section>
              )}

              {order.cancellation_reason && (
                <Section title="Cancellation">
                  <InfoRow label="Reason" value={order.cancellation_reason} multiline />
                </Section>
              )}

              <Section title="Status history">
                {order.status_history && order.status_history.length > 0 ? (
                  <div style={styles.history}>
                    {order.status_history.map((entry) => (
                      <div key={entry.id} style={styles.historyItem}>
                        <div style={styles.historyDot} />
                        <div style={{ flex: 1 }}>
                          <div style={styles.historyTransition}>
                            <span style={styles.historyFrom}>
                              {entry.from_status || "—"}
                            </span>
                            <span style={styles.historyArrow}>→</span>
                            <span style={styles.historyTo}>{entry.to_status}</span>
                          </div>
                          {entry.note && (
                            <div style={styles.historyNote}>{entry.note}</div>
                          )}
                          <div style={styles.historyDate}>
                            {formatDate(entry.created_at)}
                            {entry.changed_by_phone && ` · by ${entry.changed_by_phone}`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: "var(--text-faint)", fontSize: 13 }}>
                    No status changes logged yet.
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

function InfoRow({ label, value, multiline = false }) {
  return (
    <div style={styles.infoRow}>
      <div style={styles.infoLabel}>{label}</div>
      <div
        style={{
          ...styles.infoValue,
          whiteSpace: multiline ? "pre-wrap" : "nowrap",
          overflow: multiline ? "visible" : "hidden",
          textOverflow: multiline ? "clip" : "ellipsis",
        }}
      >
        {value}
      </div>
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
  orderTitle: {
    margin: 0,
    fontSize: 15,
    fontWeight: 500,
    color: "var(--text)",
    lineHeight: 1.4,
  },
  actionsSection: {
    background: "var(--surface-2)",
    padding: "12px 14px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    marginBottom: 16,
  },
  actionButtons: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
  },
  actionBtn: {
    padding: "8px 14px",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    fontSize: 12,
    fontWeight: 500,
    transition: "opacity 0.15s",
  },
  changeError: {
    marginTop: 10,
    padding: "8px 12px",
    background: "rgba(216,90,48,0.08)",
    color: "#D85A30",
    borderRadius: 6,
    fontSize: 12,
    border: "1px solid rgba(216,90,48,0.2)",
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
    alignItems: "flex-start",
    padding: "6px 0",
    gap: 12,
  },
  infoLabel: {
    fontSize: 12,
    color: "var(--text-faint)",
    flexShrink: 0,
    minWidth: 90,
  },
  infoValue: {
    fontSize: 13,
    color: "var(--text)",
    fontWeight: 500,
    textAlign: "right",
    flex: 1,
    maxWidth: "60%",
  },
  history: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  historyItem: {
    display: "flex",
    gap: 10,
    alignItems: "flex-start",
  },
  historyDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#2A8A8A",
    marginTop: 5,
    flexShrink: 0,
  },
  historyTransition: {
    fontSize: 13,
    color: "var(--text)",
    fontWeight: 500,
  },
  historyFrom: {
    color: "var(--text-faint)",
    textTransform: "capitalize",
  },
  historyArrow: {
    margin: "0 6px",
    color: "var(--text-faint)",
  },
  historyTo: {
    color: "#2A8A8A",
    textTransform: "capitalize",
  },
  historyNote: {
    fontSize: 12,
    color: "var(--text-muted)",
    marginTop: 2,
  },
  historyDate: {
    fontSize: 11,
    color: "var(--text-faint-2)",
    marginTop: 3,
  },
};