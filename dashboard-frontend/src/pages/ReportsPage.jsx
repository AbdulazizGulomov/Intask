// src/pages/ReportsPage.jsx
// Abuse-report moderation queue (App Store Guideline 1.2).
//
// The backend already returns open reports first, oldest first, so the row
// closest to breaching the 24-hour commitment sits at the top. This page adds
// the visual urgency: an overdue row is tinted and its age badge turns red.
import { useEffect, useState } from "react";
import {
  fetchReports,
  resolveReport,
  rejectReport,
  hideReportedJob,
  deactivateReportedUser,
} from "../api/reports";

const STATUS_STYLES = {
  open: { bg: "rgba(216,90,48,0.16)", color: "#D85A30", label: "Open" },
  resolved: { bg: "rgba(42,138,138,0.16)", color: "#2A8A8A", label: "Resolved" },
  rejected: { bg: "rgba(136,136,136,0.18)", color: "#666", label: "Rejected" },
};

const STATUS_OPTIONS = [
  { value: "open", label: "Open only" },
  { value: "", label: "All statuses" },
  { value: "resolved", label: "Resolved" },
  { value: "rejected", label: "Rejected" },
];

const REASON_LABELS = {
  spam: "Spam",
  abuse: "Abuse / harassment",
  fraud: "Fraud / scam",
  inappropriate: "Inappropriate content",
  other: "Other",
};

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Default to the open queue — that is the 24h commitment.
  const [statusFilter, setStatusFilter] = useState("open");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // id of the report currently running an action, so its buttons can disable
  const [actingId, setActingId] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);

  // Debounce search: wait 300ms after the user stops typing
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchQuery(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchReports({ page, status: statusFilter, search: searchQuery })
      .then((data) => {
        if (cancelled) return;
        setReports(data.results || []);
        setCount(data.count || 0);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load reports");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, statusFilter, searchQuery, refreshTick]);

  async function runAction(id, fn, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    setActingId(id);
    setActionError(null);
    try {
      await fn(id);
      // Refetch rather than patching in place: closing a report usually moves
      // it out of the current (open-only) filter.
      setRefreshTick((t) => t + 1);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setActionError(detail || err.message || "Action failed");
    } finally {
      setActingId(null);
    }
  }

  const pageSize = 25;
  const totalPages = Math.ceil(count / pageSize);
  const overdueCount = reports.filter((r) => r.is_overdue).length;
  const hasActiveFilters = statusFilter !== "open" || !!searchQuery;

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatAge(hours) {
    if (hours == null) return "—";
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 48) return `${hours.toFixed(1)}h`;
    return `${Math.floor(hours / 24)}d`;
  }

  function StatusBadge({ status }) {
    const style = STATUS_STYLES[status] || {
      bg: "#F0F0F0",
      color: "var(--text-muted)",
      label: status,
    };
    return <span style={{ ...styles.badge, background: style.bg, color: style.color }}>{style.label}</span>;
  }

  function AgeBadge({ report }) {
    const overdue = report.is_overdue;
    return (
      <span
        title={
          overdue
            ? `Past the ${report.sla_hours}h moderation commitment`
            : `Within the ${report.sla_hours}h moderation commitment`
        }
        style={{
          ...styles.badge,
          background: overdue ? "rgba(216,90,48,0.2)" : "var(--surface-2)",
          color: overdue ? "#D85A30" : "var(--text-muted)",
          fontWeight: overdue ? 700 : 500,
        }}
      >
        {overdue ? "⚠ " : ""}
        {formatAge(report.hours_open)}
      </span>
    );
  }

  function TargetCell({ report }) {
    if (report.target_type === "job" && report.target_job) {
      return (
        <div>
          <div style={styles.targetMain}>
            {report.target_job.title || `Job #${report.target_job.id}`}
          </div>
          <div style={styles.targetSub}>
            Job #{report.target_job.id}
            {report.target_job.is_active ? "" : " · hidden"}
          </div>
        </div>
      );
    }
    if (report.target_user) {
      return (
        <div>
          <div style={styles.targetMain}>
            {report.target_user.full_name || report.target_user.phone || `User #${report.target_user.id}`}
          </div>
          <div style={styles.targetSub}>
            User #{report.target_user.id}
            {report.target_user.is_active ? "" : " · deactivated"}
          </div>
        </div>
      );
    }
    return <span style={{ color: "var(--text-faint)" }}>—</span>;
  }

  return (
    <div>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Reports</h2>
          <p style={styles.subtitle}>
            {loading
              ? "Loading…"
              : `${count} report${count === 1 ? "" : "s"}${hasActiveFilters ? " (filtered)" : ""}`}
            {overdueCount > 0 && (
              <span style={styles.overdueNote}>
                {" · "}
                {overdueCount} past 24h
              </span>
            )}
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
            placeholder="Search comment, phone, job title…"
            style={styles.searchInput}
          />
          {searchInput && (
            <button style={styles.searchClear} onClick={() => setSearchInput("")} title="Clear search">
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
          <button
            onClick={() => {
              setSearchInput("");
              setStatusFilter("open");
              setPage(1);
            }}
            style={styles.clearBtn}
          >
            Reset to open queue
          </button>
        )}
      </div>

      {error && <div style={styles.errorBanner}>Failed to load reports: {error}</div>}
      {actionError && <div style={styles.errorBanner}>{actionError}</div>}

      {/* Table card */}
      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.loading}>Loading reports…</div>
        ) : reports.length === 0 ? (
          <div style={styles.empty}>
            {statusFilter === "open" && !searchQuery
              ? "Nothing in the queue — every report has been handled."
              : "No reports match your filters."}
          </div>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thRow}>
                  <th style={styles.th}>#</th>
                  <th style={styles.th}>Age</th>
                  <th style={styles.th}>Target</th>
                  <th style={styles.th}>Reason</th>
                  <th style={styles.th}>Reporter</th>
                  <th style={styles.th}>Status</th>
                  <th style={styles.th}>Created</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => {
                  const busy = actingId === report.id;
                  const canAct = report.status === "open";
                  return (
                    <tr
                      key={report.id}
                      style={{
                        ...styles.tr,
                        // Overdue rows are tinted so a full queue still reads
                        // at a glance which ones have breached the 24h mark.
                        background: report.is_overdue ? "rgba(216,90,48,0.06)" : undefined,
                      }}
                    >
                      <td style={{ ...styles.td, color: "var(--text-faint)" }}>#{report.id}</td>
                      <td style={styles.td}>
                        <AgeBadge report={report} />
                      </td>
                      <td style={styles.td}>
                        <TargetCell report={report} />
                      </td>
                      <td style={styles.td}>{REASON_LABELS[report.reason] || report.reason}</td>
                      <td style={{ ...styles.td, color: "var(--text-muted)" }}>
                        {report.reporter?.phone || `#${report.reporter?.id}` || "—"}
                      </td>
                      <td style={styles.td}>
                        <StatusBadge status={report.status} />
                      </td>
                      <td style={{ ...styles.td, color: "var(--text-muted)" }}>
                        {formatDate(report.created_at)}
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", whiteSpace: "nowrap" }}>
                        {canAct ? (
                          <>
                            <button
                              style={styles.actionBtn}
                              disabled={busy}
                              onClick={() => runAction(report.id, resolveReport)}
                              title="Mark as handled"
                            >
                              Resolve
                            </button>
                            <button
                              style={styles.actionBtn}
                              disabled={busy}
                              onClick={() => runAction(report.id, rejectReport)}
                              title="No violation found"
                            >
                              Reject
                            </button>
                            {report.target_job && (
                              <button
                                style={{ ...styles.actionBtn, ...styles.actionBtnDanger }}
                                disabled={busy || !report.target_job.is_active}
                                onClick={() =>
                                  runAction(
                                    report.id,
                                    hideReportedJob,
                                    `Hide job #${report.target_job.id} and resolve this report?`
                                  )
                                }
                                title="Deactivate the job and resolve"
                              >
                                Hide job
                              </button>
                            )}
                            <button
                              style={{ ...styles.actionBtn, ...styles.actionBtnDanger }}
                              disabled={busy}
                              onClick={() =>
                                runAction(
                                  report.id,
                                  deactivateReportedUser,
                                  "Deactivate this user and resolve the report? They will not be able to log in."
                                )
                              }
                              title="Deactivate the reported user and resolve"
                            >
                              Deactivate user
                            </button>
                          </>
                        ) : (
                          <span style={styles.handledBy}>
                            {report.resolved_by?.phone ? `by ${report.resolved_by.phone}` : "—"}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div style={styles.pagination}>
                <button
                  style={styles.pageBtn}
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  ← Prev
                </button>
                <span style={styles.pageInfo}>
                  Page {page} of {totalPages}
                </span>
                <button
                  style={styles.pageBtn}
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
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
  overdueNote: {
    color: "#D85A30",
    fontWeight: 600,
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
  badge: {
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 500,
    whiteSpace: "nowrap",
  },
  targetMain: {
    color: "var(--text)",
    maxWidth: 240,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  targetSub: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 2,
  },
  actionBtn: {
    padding: "5px 10px",
    marginLeft: 6,
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    fontSize: 12,
    color: "var(--text)",
    fontFamily: "inherit",
    cursor: "pointer",
  },
  actionBtnDanger: {
    color: "#D85A30",
    borderColor: "rgba(216,90,48,0.35)",
  },
  handledBy: {
    fontSize: 11,
    color: "var(--text-faint)",
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
