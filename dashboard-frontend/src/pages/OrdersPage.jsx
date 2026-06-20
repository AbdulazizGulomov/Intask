// src/pages/OrdersPage.jsx
import { useCallback, useEffect, useState } from "react";
import { fetchOrders } from "../api/dashboard";
import OrderDetailDrawer from "../components/OrderDetailDrawer";

const STATUS_STYLES = {
  scheduled: { bg: "rgba(201,169,97,0.16)", color: "#C9A961", label: "Scheduled" },
  in_progress: { bg: "rgba(42,138,138,0.16)", color: "#2A8A8A", label: "In Progress" },
  completed: { bg: "rgba(26,43,74,0.12)", color: "#1A2B4A", label: "Completed" },
  cancelled: { bg: "rgba(136,136,136,0.18)", color: "#666", label: "Cancelled" },
  disputed: { bg: "rgba(216,90,48,0.16)", color: "#D85A30", label: "Disputed" },
};

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "scheduled", label: "Scheduled" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "disputed", label: "Disputed" },
];

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Detail drawer
  const [selectedOrderId, setSelectedOrderId] = useState(null);

  // Tick used to force a refetch after a status change
  const [refreshTick, setRefreshTick] = useState(0);

  // Debounce search: wait 300ms after user stops typing
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchQuery(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Reset page when status filter changes
  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  // Fetch orders whenever page / status / search / refreshTick changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const params = { page };
    if (statusFilter) params.status = statusFilter;
    if (searchQuery) params.search = searchQuery;

    fetchOrders(params)
      .then((data) => {
        if (cancelled) return;
        setOrders(data.results || []);
        setCount(data.count || 0);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load orders");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, statusFilter, searchQuery, refreshTick]);

  // Called by the drawer after a successful status change
  const handleOrderChanged = useCallback(() => {
    setRefreshTick((t) => t + 1);
  }, []);

  const pageSize = 25;
  const totalPages = Math.ceil(count / pageSize);

  function formatPrice(price, currency = "UZS") {
    if (!price) return "—";
    const num = Number(price);
    return `${num.toLocaleString("en-US")} ${currency}`;
  }

  function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function StatusBadge({ status }) {
    const style = STATUS_STYLES[status] || {

      bg: "#F0F0F0",
      color: "var(--text-muted)",
      label: status,
    };
    return (
      <span
        style={{
          background: style.bg,
          color: style.color,
          padding: "3px 10px",
          borderRadius: 999,
          fontSize: 11,
          fontWeight: 500,
          whiteSpace: "nowrap",
        }}
      >
        {style.label}
      </span>
    );
  }

  function clearFilters() {
    setSearchInput("");
    setStatusFilter("");
    setPage(1);
  }

  const hasActiveFilters = !!statusFilter || !!searchQuery;

  return (
    <div>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Orders</h2>
          <p style={styles.subtitle}>
            {loading
              ? "Loading…"
              : `${count} order${count === 1 ? "" : "s"}${hasActiveFilters ? " (filtered)" : ""}`}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.searchWrap}>
          <span style={styles.searchIcon}>🔍</span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search title, phone, address…"
            style={styles.searchInput}
          />
          {searchInput && (
            <button
              style={styles.searchClear}
              onClick={() => setSearchInput("")}
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={styles.select}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {hasActiveFilters && (
          <button onClick={clearFilters} style={styles.clearBtn}>
            Clear filters
          </button>
        )}
      </div>

      {error && (
        <div style={styles.errorBanner}>Failed to load orders: {error}</div>
      )}

      {/* Table card */}
      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.loading}>Loading orders…</div>
        ) : orders.length === 0 ? (
          <div style={styles.empty}>
            {hasActiveFilters
              ? "No orders match your filters."
              : "No orders found."}
          </div>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thRow}>
                  <th style={styles.th}>#</th>
                  <th style={styles.th}>Title</th>
                  <th style={styles.th}>Employer</th>
                  <th style={styles.th}>Worker</th>
                  <th style={styles.th}>Status</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Price</th>
                  <th style={styles.th}>Created</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr
                    key={order.id}
                    style={{ ...styles.tr, cursor: "pointer" }}
                    onClick={() => setSelectedOrderId(order.id)}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "var(--surface-2)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "")
                    }
                  >
                    <td style={{ ...styles.td, color: "var(--text-faint)" }}>#{order.id}</td>
                    <td style={styles.td}>{order.title || "—"}</td>
                    <td style={{ ...styles.td, color: "var(--text-muted)" }}>
                      {order.employer_phone || "—"}
                    </td>
                    <td style={{ ...styles.td, color: "var(--text-muted)" }}>
                      {order.worker_phone || "—"}
                    </td>
                    <td style={styles.td}>
                      <StatusBadge status={order.status} />
                    </td>
                    <td
                      style={{
                        ...styles.td,
                        textAlign: "right",
                        fontWeight: 500,
                      }}
                    >
                      {formatPrice(order.agreed_price, order.currency)}
                    </td>
                    <td style={{ ...styles.td, color: "var(--text-faint)" }}>
                      {formatDate(order.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div style={styles.pagination}>
                <button
                  style={{
                    ...styles.pageBtn,
                    opacity: page === 1 ? 0.4 : 1,
                    cursor: page === 1 ? "not-allowed" : "pointer",
                  }}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  ← Prev
                </button>
                <span style={styles.pageInfo}>
                  Page {page} of {totalPages}
                </span>
                <button
                  style={{
                    ...styles.pageBtn,
                    opacity: page === totalPages ? 0.4 : 1,
                    cursor: page === totalPages ? "not-allowed" : "pointer",
                  }}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail drawer */}
      <OrderDetailDrawer
        orderId={selectedOrderId}
        onClose={() => setSelectedOrderId(null)}
        onOrderChanged={handleOrderChanged}
      />
    </div>
  );
}

// ===== Inline styles =====
const styles = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  title: {
    margin: 0,
    fontSize: 18,
    fontWeight: 600,
    color: "var(--text)",
    fontFamily: "system-ui, sans-serif",
  },
  subtitle: {
    margin: "2px 0 0",
    fontSize: 12,
    color: "var(--text-faint)",
  },
  toolbar: {
    display: "flex",
    gap: 10,
    marginBottom: 12,
    fontFamily: "system-ui, sans-serif",
  },
  searchWrap: {
    position: "relative",
    flex: 1,
    maxWidth: 360,
  },
  searchIcon: {
    position: "absolute",
    left: 12,
    top: "50%",
    transform: "translateY(-50%)",
    fontSize: 13,
    color: "var(--text-faint)",
    pointerEvents: "none",
  },
  searchInput: {
    width: "100%",
    padding: "9px 32px 9px 32px",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 13,
    outline: "none",
    color: "var(--text)",
    background: "var(--card)",
    fontFamily: "inherit",
    boxSizing: "border-box",
  },
  searchClear: {
    position: "absolute",
    right: 8,
    top: "50%",
    transform: "translateY(-50%)",
    background: "transparent",
    border: "none",
    color: "var(--text-faint)",
    cursor: "pointer",
    fontSize: 13,
    padding: 4,
  },
  select: {
    padding: "9px 14px",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 13,
    color: "var(--text)",
    background: "var(--card)",
    fontFamily: "inherit",
    cursor: "pointer",
  },
  clearBtn: {
    padding: "9px 14px",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 13,
    color: "#D85A30",
    background: "var(--card)",
    fontFamily: "inherit",
    cursor: "pointer",
  },
  errorBanner: {
    background: "rgba(216,90,48,0.08)",
    color: "#D85A30",
    padding: "10px 14px",
    borderRadius: 8,
    fontSize: 13,
    marginBottom: 12,
    border: "1px solid rgba(216,90,48,0.2)",
    fontFamily: "system-ui, sans-serif",
  },
  tableCard: {
    background: "var(--card)",
    borderRadius: 10,
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
    overflow: "hidden",
  },
  loading: {
    padding: "40px 20px",
    textAlign: "center",
    color: "var(--text-faint)",
    fontSize: 13,
  },
  empty: {
    padding: "40px 20px",
    textAlign: "center",
    color: "var(--text-faint)",
    fontSize: 13,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  },
  thRow: {
    background: "var(--surface-2)",
    borderBottom: "1px solid var(--border)",
  },
  th: {
    padding: "10px 14px",
    textAlign: "left",
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  tr: {
    borderBottom: "1px solid var(--border-subtle)",
  },
  td: {
    padding: "12px 14px",
    color: "var(--text)",
    verticalAlign: "middle",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
    padding: "12px 14px",
    background: "var(--surface-2)",
    borderTop: "1px solid var(--border)",
  },
  pageBtn: {
    padding: "6px 12px",
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    fontSize: 12,
    color: "var(--text)",
  },
  pageInfo: {
    fontSize: 12,
    color: "var(--text-faint)",
  },
};