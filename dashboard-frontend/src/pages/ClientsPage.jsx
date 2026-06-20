// src/pages/ClientsPage.jsx
import { useEffect, useState } from "react";
import { fetchClients } from "../api/dashboard";
import ClientDetailDrawer from "../components/ClientDetailDrawer";

export default function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);

  // Detail drawer
  const [selectedClientId, setSelectedClientId] = useState(null);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchQuery(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
  }, [activeOnly]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const params = { page };
    if (searchQuery) params.search = searchQuery;
    if (activeOnly) params.is_active = "true";

    fetchClients(params)
      .then((data) => {
        if (cancelled) return;
        setClients(data.results || []);
        setCount(data.count || 0);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load clients");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, searchQuery, activeOnly]);

  const pageSize = 25;
  const totalPages = Math.ceil(count / pageSize);

  function formatMoney(amount) {
    if (!amount) return "—";
    if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(2)}M`;
    if (amount >= 1_000) return `${(amount / 1_000).toFixed(0)}K`;
    return `${amount}`;
  }

  function formatDate(iso) {
    if (!iso) return "Never";
    const d = new Date(iso);
    const now = new Date();
    const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return `${Math.floor(diffDays / 365)}y ago`;
  }

  function getCancellationStyle(rate) {
    if (rate === 0) return { color: "#2A8A8A", weight: 500 };
    if (rate < 20) return { color: "#1A2B4A", weight: 500 };
    if (rate < 40) return { color: "#C9A961", weight: 600 };
    return { color: "#D85A30", weight: 600 };
  }

  function getRowHighlight(client) {
    if (client.total_spent >= 5_000_000) return "#FFFBF0";
    return "";
  }

  function clearFilters() {
    setSearchInput("");
    setActiveOnly(false);
    setPage(1);
  }

  const hasActiveFilters = !!searchQuery || activeOnly;

  return (
    <div>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Clients</h2>
          <p style={styles.subtitle}>
            {loading
              ? "Loading…"
              : `${count} employer${count === 1 ? "" : "s"} registered${hasActiveFilters ? " (filtered)" : ""}`}
          </p>
        </div>
      </div>

      <div style={styles.toolbar}>
        <div style={styles.searchWrap}>
          <span style={styles.searchIcon}>🔍</span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by name or phone…"
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

        <label style={styles.checkboxWrap}>
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            style={styles.checkbox}
          />
          <span>Active only</span>
        </label>

        {hasActiveFilters && (
          <button onClick={clearFilters} style={styles.clearBtn}>
            Clear filters
          </button>
        )}
      </div>

      {error && (
        <div style={styles.errorBanner}>Failed to load clients: {error}</div>
      )}

      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.loading}>Loading clients…</div>
        ) : clients.length === 0 ? (
          <div style={styles.empty}>
            {hasActiveFilters
              ? "No clients match your filters."
              : "No clients found."}
          </div>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thRow}>
                  <th style={styles.th}>Client</th>
                  <th style={styles.th}>Phone</th>
                  <th style={{ ...styles.th, textAlign: "center" }}>Status</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Total orders</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Completed</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Total spent</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Cancellation</th>
                  <th style={styles.th}>Last order</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((client) => {
                  const isVIP = client.total_spent >= 5_000_000;
                  const cancellationStyle = getCancellationStyle(client.cancellation_rate);

                  return (
                    <tr
                      key={client.id}
                      style={{
                        ...styles.tr,
                        background: getRowHighlight(client),
                        cursor: "pointer",
                      }}
                      onClick={() => setSelectedClientId(client.id)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "var(--surface-2)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = getRowHighlight(client);
                      }}
                    >
                      <td style={styles.td}>
                        <div style={styles.clientCell}>
                          <div style={styles.avatar}>
                            {(client.full_name || client.username || client.phone || "?")
                              .charAt(0)
                              .toUpperCase()}
                          </div>
                          <div style={{ minWidth: 0 }}>
                            <div style={styles.clientName}>
                              {client.full_name?.trim() ||
                                client.username ||
                                client.phone ||
                                "Unnamed client"}
                              {isVIP && <span style={styles.vipBadge}>VIP</span>}
                            </div>
                            <div style={styles.clientId}>#{client.id}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ ...styles.td, color: "var(--text-muted)", fontFamily: "monospace", fontSize: 12 }}>
                        {client.phone || "—"}
                      </td>
                      <td style={{ ...styles.td, textAlign: "center" }}>
                        <span
                          style={{
                            ...styles.statusDot,
                            background: client.is_active ? "#2A8A8A" : "#999",
                          }}
                          title={client.is_active ? "Active" : "Inactive"}
                        />
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", fontWeight: 500 }}>
                        {client.total_orders || 0}
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", color: "var(--text-muted)" }}>
                        {client.completed_orders || 0}
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", fontWeight: 600, color: "var(--text)" }}>
                        {client.total_spent > 0
                          ? `${formatMoney(client.total_spent)} UZS`
                          : "—"}
                      </td>
                      <td
                        style={{
                          ...styles.td,
                          textAlign: "right",
                          color: cancellationStyle.color,
                          fontWeight: cancellationStyle.weight,
                        }}
                      >
                        {client.cancellation_rate != null
                          ? `${client.cancellation_rate}%`
                          : "—"}
                      </td>
                      <td style={{ ...styles.td, color: "var(--text-faint)", fontSize: 12 }}>
                        {formatDate(client.last_order_at)}
                      </td>
                    </tr>
                  );
                })}
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
      <ClientDetailDrawer
        clientId={selectedClientId}
        onClose={() => setSelectedClientId(null)}
      />
    </div>
  );
}

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
    marginBottom: 14,
    fontFamily: "system-ui, sans-serif",
    alignItems: "center",
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
  checkboxWrap: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 13,
    color: "var(--text)",
    cursor: "pointer",
    padding: "9px 12px",
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    userSelect: "none",
  },
  checkbox: {
    accentColor: "#2A8A8A",
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
    transition: "background 0.1s",
  },
  td: {
    padding: "12px 14px",
    color: "var(--text)",
    verticalAlign: "middle",
  },
  clientCell: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    minWidth: 0,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A8A8A 0%, #1A2B4A 100%)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 13,
    flexShrink: 0,
  },
  clientName: {
    fontWeight: 500,
    color: "var(--text)",
    fontSize: 13,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  clientId: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 1,
  },
  vipBadge: {
    background: "#C9A961",
    color: "#fff",
    padding: "1px 6px",
    borderRadius: 4,
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: 0.5,
  },
  statusDot: {
    display: "inline-block",
    width: 10,
    height: 10,
    borderRadius: "50%",
    border: "2px solid #fff",
    boxShadow: "0 0 0 1px var(--border)",
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