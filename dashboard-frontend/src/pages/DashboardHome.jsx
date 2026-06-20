// src/pages/DashboardHome.jsx
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";

import {
  fetchStats,
  fetchOrdersTrendChart,
  fetchStatusMixChart,
  fetchTopProfessionsChart,
  fetchRevenueByDistrictChart,
} from "../api/dashboard";
import KpiCard from "../components/KpiCard";

const STATUS_COLORS = {
  Scheduled: "#C9A961",
  "In Progress": "#2A8A8A",
  Completed: "#1A2B4A",
  Cancelled: "#888",
  Disputed: "#D85A30",
};

export default function DashboardHome() {
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [trendData, setTrendData] = useState([]);
  const [trendLoading, setTrendLoading] = useState(true);

  const [statusData, setStatusData] = useState([]);
  const [statusLoading, setStatusLoading] = useState(true);

  const [professionsData, setProfessionsData] = useState([]);
  const [professionsLoading, setProfessionsLoading] = useState(true);

  const [districtData, setDistrictData] = useState([]);
  const [districtLoading, setDistrictLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    fetchStats()
      .then((data) => !cancelled && setStats(data))
      .catch((err) => !cancelled && setError(err.message || "Failed to load stats"))
      .finally(() => !cancelled && setStatsLoading(false));

    fetchOrdersTrendChart()
      .then((data) => {
        if (cancelled) return;
        setTrendData(
          data.labels.map((label, i) => ({
            day: label,
            Created: data.datasets[0]?.data[i] ?? 0,
            Completed: data.datasets[1]?.data[i] ?? 0,
          }))
        );
      })
      .catch((err) => console.error("Trend chart error:", err))
      .finally(() => !cancelled && setTrendLoading(false));

    fetchStatusMixChart()
      .then((data) => {
        if (cancelled) return;
        setStatusData(
          data.labels.map((label, i) => ({ name: label, value: data.data[i] ?? 0 }))
        );
      })
      .catch((err) => console.error("Status chart error:", err))
      .finally(() => !cancelled && setStatusLoading(false));

    fetchTopProfessionsChart()
      .then((data) => {
        if (cancelled) return;
        setProfessionsData(
          data.labels.map((label, i) => ({ name: label, orders: data.data[i] ?? 0 }))
        );
      })
      .catch((err) => console.error("Professions chart error:", err))
      .finally(() => !cancelled && setProfessionsLoading(false));

    fetchRevenueByDistrictChart()
      .then((data) => {
        if (cancelled) return;
        setDistrictData(
          data.labels.map((label, i) => ({
            name: label,
            revenue: data.data[i] ?? 0,
          }))
        );
      })
      .catch((err) => console.error("District chart error:", err))
      .finally(() => !cancelled && setDistrictLoading(false));

    return () => {
      cancelled = true;
    };
  }, []);

  function formatMoney(n) {
    if (n == null) return "—";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return `${n}`;
  }
  function formatChange(pct) {
    if (pct == null) return "vs previous week";
    const sign = pct >= 0 ? "+" : "";
    return `${sign}${pct.toFixed(1)}% vs prev week`;
  }

  const totalOrders = statusData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div>
      {error && (
        <div style={styles.errorBanner}>
          Failed to load dashboard data: {error}
        </div>
      )}

      {/* KPI grid */}
      <div style={styles.kpiGrid}>
        <KpiCard
          label="Active orders"
          value={statsLoading ? "" : stats?.active_orders ?? "—"}
          accent={
            statsLoading
              ? ""
              : stats?.active_orders_today
                ? `+${stats.active_orders_today} today`
                : "no new today"
          }
          icon="📋"
          loading={statsLoading}
        />
        <KpiCard
          label="Completed (week)"
          value={statsLoading ? "" : stats?.completed_week ?? "—"}
          accent={statsLoading ? "" : "this week"}
          accentColor="var(--text-faint)"
          icon="✅"
          loading={statsLoading}
        />
        <KpiCard
          label="Revenue (week)"
          value={statsLoading ? "" : `${formatMoney(stats?.revenue_week)} UZS`}
          accent={statsLoading ? "" : formatChange(stats?.revenue_change_pct)}
          accentColor={stats?.revenue_change_pct >= 0 ? "#2A8A8A" : "#D85A30"}
          icon="💰"
          loading={statsLoading}
        />
        <KpiCard
          label="Disputes"
          value={statsLoading ? "" : stats?.disputes ?? 0}
          accent={statsLoading ? "" : "needs review"}
          accentColor="#C9A961"
          icon="⚠️"
          loading={statsLoading}
        />
      </div>

      {/* Charts row 1 — Trend (wider) + Status mix */}
      <div style={styles.chartsRow}>
        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Orders trend</h3>
            <span style={styles.chartSubtitle}>Last 7 days</span>
          </div>
          <div style={{ width: "100%", height: 260 }}>
            {trendLoading ? (
              <div style={styles.chartLoading}>Loading chart…</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
                  <XAxis dataKey="day" stroke="#888" fontSize={12} tickLine={false} />
                  <YAxis stroke="#888" fontSize={12} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                  <Line
                    type="monotone"
                    dataKey="Created"
                    stroke="#2A8A8A"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#2A8A8A" }}
                    activeDot={{ r: 6 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="Completed"
                    stroke="#1A2B4A"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 4, fill: "#1A2B4A" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Order status mix</h3>
            <span style={styles.chartSubtitle}>{totalOrders} total</span>
          </div>
          <div style={{ width: "100%", height: 260, position: "relative" }}>
            {statusLoading ? (
              <div style={styles.chartLoading}>Loading chart…</div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      {statusData.map((entry, i) => (
                        <Cell
                          key={i}
                          fill={STATUS_COLORS[entry.name] || "#999"}
                          stroke="none"
                        />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend
                      iconType="circle"
                      wrapperStyle={{ fontSize: 11, paddingTop: 6 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div style={styles.donutCenter}>
                  <div style={styles.donutCenterNumber}>{totalOrders}</div>
                  <div style={styles.donutCenterLabel}>orders</div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Charts row 2 — Top professions (left) + Revenue by district (right) */}
      <div style={styles.chartsRow}>
        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Top professions</h3>
            <span style={styles.chartSubtitle}>By order count</span>
          </div>
          <div style={{ width: "100%", height: 260 }}>
            {professionsLoading ? (
              <div style={styles.chartLoading}>Loading chart…</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={professionsData}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 30, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" horizontal={false} />
                  <XAxis type="number" stroke="#888" fontSize={11} tickLine={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#888"
                    fontSize={11}
                    tickLine={false}
                    width={110}
                  />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="orders" fill="#2A8A8A" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Revenue by district */}
        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Revenue by district</h3>
            <span style={styles.chartSubtitle}>Completed orders, M UZS</span>
          </div>
          <div style={{ width: "100%", height: 260 }}>
            {districtLoading ? (
              <div style={styles.chartLoading}>Loading chart…</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={districtData}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" vertical={false} />
                  <XAxis
                    dataKey="name"
                    stroke="#888"
                    fontSize={11}
                    tickLine={false}
                    interval={0}
                  />
                  <YAxis
                    stroke="#888"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(v) => `${v}M`}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v) => [`${v}M UZS`, "Revenue"]}
                  />
                  <Bar dataKey="revenue" fill="#1A2B4A" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ===== Inline styles =====
const tooltipStyle = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 13,
};

const styles = {
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 12,
    marginBottom: 16,
  },
  chartsRow: {
    display: "grid",
    gridTemplateColumns: "1.4fr 1fr",
    gap: 12,
    marginBottom: 12,
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
  chartCard: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "16px 18px",
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  chartHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 12,
  },
  chartTitle: {
    margin: 0,
    fontSize: 14,
    fontWeight: 600,
    color: "var(--text)",
  },
  chartSubtitle: {
    fontSize: 11,
    color: "var(--text-faint)",
  },
  chartLoading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    color: "var(--text-faint)",
    fontSize: 13,
  },
  donutCenter: {
    position: "absolute",
    top: "calc(50% - 14px)",
    left: 0,
    right: 0,
    textAlign: "center",
    pointerEvents: "none",
  },
  donutCenterNumber: {
    fontSize: 22,
    fontWeight: 600,
    color: "var(--text)",
    lineHeight: 1,
  },
  donutCenterLabel: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 2,
  },
};