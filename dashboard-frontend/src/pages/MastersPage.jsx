// src/pages/MastersPage.jsx
import { useEffect, useState } from "react";
import { fetchMasters } from "../api/dashboard";
import MasterDetailDrawer from "../components/MasterDetailDrawer";

export default function MastersPage() {
  const [masters, setMasters] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);

  // List of unique professions extracted from the data we receive
  const [allProfessions, setAllProfessions] = useState([]);
  const [professionFilter, setProfessionFilter] = useState("");

  // Detail drawer
  const [selectedMasterId, setSelectedMasterId] = useState(null);

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchQuery(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [professionFilter, activeOnly]);

  // Fetch masters
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const params = { page };
    if (searchQuery) params.search = searchQuery;
    if (activeOnly) params.is_active = "true";

    fetchMasters(params)
      .then((data) => {
        if (cancelled) return;
        setMasters(data.results || []);
        setCount(data.count || 0);
        setError(null);

        // Collect unique professions for the filter dropdown
        const uniqueProfs = new Set();
        (data.results || []).forEach((m) => {
          if (m.profession_name) uniqueProfs.add(m.profession_name);
        });
        setAllProfessions((prev) => {
          const merged = new Set([...prev, ...uniqueProfs]);
          return Array.from(merged).sort();
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load masters");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, searchQuery, activeOnly]);

  // Apply client-side profession filter
  const filteredMasters = professionFilter
    ? masters.filter((m) => m.profession_name === professionFilter)
    : masters;

  const pageSize = 25;
  const totalPages = Math.ceil(count / pageSize);

  function getInitials(master) {
    const first = (master.first_name || "").trim();
    const last = (master.last_name || "").trim();
    if (first && last) return `${first[0]}${last[0]}`.toUpperCase();
    if (first) return first.slice(0, 2).toUpperCase();
    if (master.phone) return master.phone.slice(-2);
    return "??";
  }

  function StarRating({ rating }) {
    if (rating == null) return <span style={styles.noRating}>No ratings</span>;
    const rounded = Math.round(rating * 10) / 10;
    return (
      <span style={styles.rating}>
        <span style={{ color: "#C9A961" }}>★</span> {rounded}
      </span>
    );
  }

  function clearFilters() {
    setSearchInput("");
    setProfessionFilter("");
    setActiveOnly(false);
    setPage(1);
  }

  const hasActiveFilters = !!searchQuery || !!professionFilter || activeOnly;

  return (
    <div>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Masters</h2>
          <p style={styles.subtitle}>
            {loading
              ? "Loading…"
              : `${count} worker${count === 1 ? "" : "s"} registered${
                  hasActiveFilters && filteredMasters.length !== masters.length
                    ? ` · ${filteredMasters.length} shown`
                    : ""
                }`}
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
            placeholder="Search by name, phone…"
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
          value={professionFilter}
          onChange={(e) => setProfessionFilter(e.target.value)}
          style={styles.select}
        >
          <option value="">All professions</option>
          {allProfessions.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>

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
        <div style={styles.errorBanner}>Failed to load masters: {error}</div>
      )}

      {/* Card grid */}
      {loading ? (
        <div style={styles.loadingBox}>Loading masters…</div>
      ) : filteredMasters.length === 0 ? (
        <div style={styles.emptyBox}>
          {hasActiveFilters
            ? "No masters match your filters."
            : "No masters found."}
        </div>
      ) : (
        <>
          <div style={styles.grid}>
            {filteredMasters.map((master) => (
              <div
                key={master.id}
                style={styles.card}
                onClick={() => setSelectedMasterId(master.id)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#2A8A8A";
                  e.currentTarget.style.transform = "translateY(-2px)";
                  e.currentTarget.style.boxShadow =
                    "0 8px 24px rgba(0,0,0,0.08)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.transform = "";
                  e.currentTarget.style.boxShadow = "";
                }}
              >
                <div style={styles.cardTop}>
                  <div style={styles.avatarWrap}>
                    <div
                      style={{
                        ...styles.statusDot,
                        background: master.is_active ? "#2A8A8A" : "#999",
                      }}
                      title={master.is_active ? "Active" : "Inactive"}
                    />
                    <div style={styles.avatar}>{getInitials(master)}</div>
                  </div>
                </div>

                <div style={styles.name}>
                  {master.full_name?.trim() || master.phone || "Unknown"}
                </div>

                <div style={styles.profession}>
                  {master.profession_name || "—"}
                </div>

                <div style={styles.statsRow}>
                  <div style={styles.statBox}>
                    <div style={styles.statValue}>
                      <StarRating rating={master.avg_rating} />
                    </div>
                  </div>
                  <div style={styles.statDivider} />
                  <div style={styles.statBox}>
                    <div style={styles.statValueText}>
                      {master.completed_orders || 0}
                    </div>
                    <div style={styles.statLabel}>orders</div>
                  </div>
                </div>

                <div style={styles.phone}>{master.phone || "—"}</div>
              </div>
            ))}
          </div>

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

      {/* Detail drawer */}
      <MasterDetailDrawer
        masterId={selectedMasterId}
        onClose={() => setSelectedMasterId(null)}
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
  loadingBox: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "40px 20px",
    textAlign: "center",
    color: "var(--text-faint)",
    fontSize: 13,
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  emptyBox: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "40px 20px",
    textAlign: "center",
    color: "var(--text-faint)",
    fontSize: 13,
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
    gap: 14,
    fontFamily: "system-ui, sans-serif",
  },
  card: {
    background: "var(--card)",
    borderRadius: 12,
    padding: "20px 16px",
    border: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    cursor: "pointer",
    transition: "border-color 0.15s, transform 0.15s, box-shadow 0.15s",
  },
  cardTop: {
    marginBottom: 12,
  },
  avatarWrap: {
    position: "relative",
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A8A8A 0%, #1A2B4A 100%)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 22,
    fontFamily: "system-ui, sans-serif",
  },
  statusDot: {
    position: "absolute",
    bottom: 2,
    right: 2,
    width: 14,
    height: 14,
    borderRadius: "50%",
    border: "2px solid #fff",
    zIndex: 1,
  },
  name: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--text)",
    marginBottom: 2,
    maxWidth: "100%",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    width: "100%",
  },
  profession: {
    fontSize: 12,
    color: "#2A8A8A",
    fontWeight: 500,
    marginBottom: 12,
    maxWidth: "100%",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    width: "100%",
  },
  statsRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    width: "100%",
    padding: "10px 0",
    borderTop: "1px solid var(--border-subtle)",
    borderBottom: "1px solid var(--border-subtle)",
    marginBottom: 10,
  },
  statBox: {
    flex: 1,
    textAlign: "center",
  },
  statDivider: {
    width: 1,
    height: 24,
    background: "var(--border-subtle)",
  },
  statValue: {
    fontSize: 13,
    color: "var(--text)",
    fontWeight: 600,
  },
  statValueText: {
    fontSize: 16,
    color: "var(--text)",
    fontWeight: 600,
  },
  statLabel: {
    fontSize: 10,
    color: "var(--text-faint)",
    textTransform: "uppercase",
    letterSpacing: 0.3,
    marginTop: 2,
  },
  rating: {
    fontSize: 13,
    color: "var(--text)",
    fontWeight: 600,
  },
  noRating: {
    fontSize: 11,
    color: "var(--text-faint-2)",
  },
  phone: {
    fontSize: 11,
    color: "var(--text-faint)",
    fontFamily: "monospace",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
    marginTop: 20,
  },
  pageBtn: {
    padding: "8px 14px",
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    fontSize: 13,
    color: "var(--text)",
  },
  pageInfo: {
    fontSize: 12,
    color: "var(--text-faint)",
  },
};