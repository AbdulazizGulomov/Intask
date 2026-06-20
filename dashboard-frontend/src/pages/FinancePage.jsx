// src/pages/FinancePage.jsx
import { useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// =====================================================
// MOCK DATA — replace with real /api/dashboard/finance/ when Payme is live
// =====================================================

// 30 days of revenue (more recent = higher because business is growing!)
const REVENUE_TREND = Array.from({ length: 30 }, (_, i) => {
  const base = 600_000 + i * 25_000;
  const noise = Math.sin(i * 0.7) * 200_000;
  return {
    day: `${i + 1}`,
    revenue: Math.round((base + noise) / 1000) * 1000,
  };
});

// Commission by week (last 8 weeks)
const COMMISSION_BY_WEEK = [
  { week: "W-7", commission: 820_000 },
  { week: "W-6", commission: 940_000 },
  { week: "W-5", commission: 1_120_000 },
  { week: "W-4", commission: 1_080_000 },
  { week: "W-3", commission: 1_350_000 },
  { week: "W-2", commission: 1_280_000 },
  { week: "W-1", commission: 1_510_000 },
  { week: "This", commission: 1_640_000 },
];

const TOP_WORKERS = [
  { name: "Akmal Karimov", profession: "Usta", earned: 8_240_000, orders: 24 },
  { name: "Bobur Saidov", profession: "Elektrik", earned: 6_180_000, orders: 19 },
  { name: "Dilshod Aliyev", profession: "Bo'yoqchi", earned: 4_920_000, orders: 16 },
  { name: "Sherzod Yusupov", profession: "Bog'bon", earned: 3_510_000, orders: 12 },
  { name: "Rustam Toshev", profession: "Kompyuter ustasi", earned: 2_870_000, orders: 9 },
];

const TOP_CLIENTS = [
  { name: "Aziz Nazarov", phone: "+998901111101", spent: 6_840_000, orders: 22 },
  { name: "Madina Yusupova", phone: "+998901111102", spent: 5_120_000, orders: 18 },
  { name: "Jasur Karimov", phone: "+998901111103", spent: 4_350_000, orders: 15 },
  { name: "Nilufar Toshkentova", phone: "+998901111104", spent: 3_780_000, orders: 13 },
  { name: "Hasan Rakhimov", phone: "+998901111105", spent: 2_910_000, orders: 10 },
];

const RECENT_TRANSACTIONS = [
  { id: 4821, type: "payment_in", client: "+998901111103", amount: 480_000, method: "Payme", time: "2 min ago", status: "completed" },
  { id: 4820, type: "payout_to_worker", worker: "+998902222204", amount: 432_000, method: "Card", time: "12 min ago", status: "completed" },
  { id: 4819, type: "commission", amount: 48_000, method: "—", time: "12 min ago", status: "completed" },
  { id: 4818, type: "payment_in", client: "+998901111101", amount: 1_240_000, method: "Click", time: "1h ago", status: "completed" },
  { id: 4817, type: "payout_to_worker", worker: "+998902222207", amount: 1_116_000, method: "Card", time: "1h ago", status: "pending" },
  { id: 4816, type: "commission", amount: 124_000, method: "—", time: "1h ago", status: "completed" },
  { id: 4815, type: "payment_in", client: "+998901111102", amount: 350_000, method: "Payme", time: "3h ago", status: "completed" },
  { id: 4814, type: "refund", client: "+998901111104", amount: -180_000, method: "Payme", time: "5h ago", status: "completed" },
];

// =====================================================
// COMPONENT
// =====================================================

export default function FinancePage() {
  const [period, setPeriod] = useState("week");

  function formatMoney(n) {
    if (n == null) return "—";
    const abs = Math.abs(n);
    const sign = n < 0 ? "-" : "";
    if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(2)}M`;
    if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(0)}K`;
    return `${sign}${abs}`;
  }

  // Compute KPIs
  const grossRevenue = 15_150_000;
  const platformCommission = 1_515_000;
  const avgOrderValue = 302_000;
  const pendingPayouts = 2_840_000;

  return (
    <div>
      {/* Demo banner */}
      <div style={styles.demoBanner}>
        <span style={{ marginRight: 8 }}>⚡</span>
        <strong>Demo mode:</strong> This page shows sample data. Real numbers
        will appear once Payme/Click integration is live.
      </div>

      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Finance</h2>
          <p style={styles.subtitle}>Revenue, commissions, and payouts</p>
        </div>
        <div style={styles.periodSelector}>
          {["week", "month", "year"].map((p) => (
            <button
              key={p}
              style={{
                ...styles.periodBtn,
                ...(period === p ? styles.periodBtnActive : {}),
              }}
              onClick={() => setPeriod(p)}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* KPI grid */}
      <div style={styles.kpiGrid}>
        <KpiCard
          label="Gross revenue"
          value={`${formatMoney(grossRevenue)} UZS`}
          accent="+851% vs last period"
          accentColor="#2A8A8A"
          icon="💰"
        />
        <KpiCard
          label="Platform commission"
          value={`${formatMoney(platformCommission)} UZS`}
          accent="10% take rate"
          accentColor="var(--text-faint)"
          icon="📊"
        />
        <KpiCard
          label="Avg order value"
          value={`${formatMoney(avgOrderValue)} UZS`}
          accent="+12% this week"
          accentColor="#2A8A8A"
          icon="📈"
        />
        <KpiCard
          label="Pending payouts"
          value={`${formatMoney(pendingPayouts)} UZS`}
          accent="awaiting transfer"
          accentColor="#C9A961"
          icon="⏳"
        />
      </div>

      {/* Charts row */}
      <div style={styles.chartsRow}>
        {/* Revenue trend */}
        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Revenue trend</h3>
            <span style={styles.chartSubtitle}>Last 30 days</span>
          </div>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={REVENUE_TREND} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
                <XAxis dataKey="day" stroke="#888" fontSize={11} tickLine={false} interval={3} />
                <YAxis
                  stroke="#888"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1_000_000).toFixed(1)}M`}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v) => [`${formatMoney(v)} UZS`, "Revenue"]}
                  labelFormatter={(label) => `Day ${label}`}
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="#2A8A8A"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Commission by week */}
        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Commission earned</h3>
            <span style={styles.chartSubtitle}>Last 8 weeks</span>
          </div>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={COMMISSION_BY_WEEK} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" vertical={false} />
                <XAxis dataKey="week" stroke="#888" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#888"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1_000_000).toFixed(1)}M`}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v) => [`${formatMoney(v)} UZS`, "Commission"]}
                />
                <Bar dataKey="commission" fill="#1A2B4A" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top earners + top spenders */}
      <div style={styles.chartsRow}>
        <div style={styles.tableCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>👷 Top earning workers</h3>
            <span style={styles.chartSubtitle}>This month</span>
          </div>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thRow}>
                <th style={styles.th}>Worker</th>
                <th style={styles.th}>Profession</th>
                <th style={{ ...styles.th, textAlign: "right" }}>Orders</th>
                <th style={{ ...styles.th, textAlign: "right" }}>Earned</th>
              </tr>
            </thead>
            <tbody>
              {TOP_WORKERS.map((w, i) => (
                <tr key={i} style={styles.tr}>
                  <td style={styles.td}>
                    <div style={styles.workerCell}>
                      <span style={styles.rankBadge}>{i + 1}</span>
                      <span>{w.name}</span>
                    </div>
                  </td>
                  <td style={{ ...styles.td, color: "#2A8A8A", fontSize: 12 }}>{w.profession}</td>
                  <td style={{ ...styles.td, textAlign: "right", color: "var(--text-muted)" }}>{w.orders}</td>
                  <td style={{ ...styles.td, textAlign: "right", fontWeight: 600, color: "var(--text)" }}>
                    {formatMoney(w.earned)} UZS
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={styles.tableCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>🏆 Top spending clients</h3>
            <span style={styles.chartSubtitle}>This month</span>
          </div>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thRow}>
                <th style={styles.th}>Client</th>
                <th style={{ ...styles.th, textAlign: "right" }}>Orders</th>
                <th style={{ ...styles.th, textAlign: "right" }}>Spent</th>
              </tr>
            </thead>
            <tbody>
              {TOP_CLIENTS.map((c, i) => (
                <tr key={i} style={styles.tr}>
                  <td style={styles.td}>
                    <div style={styles.workerCell}>
                      <span style={{ ...styles.rankBadge, background: "#C9A961" }}>{i + 1}</span>
                      <div>
                        <div style={{ fontWeight: 500 }}>{c.name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-faint)", fontFamily: "monospace" }}>
                          {c.phone}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ ...styles.td, textAlign: "right", color: "var(--text-muted)" }}>{c.orders}</td>
                  <td style={{ ...styles.td, textAlign: "right", fontWeight: 600, color: "var(--text)" }}>
                    {formatMoney(c.spent)} UZS
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent transactions */}
      <div style={styles.transactionsCard}>
        <div style={styles.chartHeader}>
          <h3 style={styles.chartTitle}>💳 Recent transactions</h3>
          <span style={styles.chartSubtitle}>Live feed (mock)</span>
        </div>
        <div style={styles.transactionsList}>
          {RECENT_TRANSACTIONS.map((tx) => (
            <TransactionRow key={tx.id} tx={tx} formatMoney={formatMoney} />
          ))}
        </div>
      </div>
    </div>
  );
}

// =====================================================
// SUB-COMPONENTS
// =====================================================

function KpiCard({ label, value, accent, accentColor, icon }) {
  return (
    <div style={styles.kpiCard}>
      <div style={styles.kpiHeader}>
        <span style={styles.kpiLabel}>{label}</span>
        {icon && <span style={styles.kpiIcon}>{icon}</span>}
      </div>
      <div style={styles.kpiValue}>{value}</div>
      {accent && <div style={{ ...styles.kpiAccent, color: accentColor }}>{accent}</div>}
    </div>
  );
}

function TransactionRow({ tx, formatMoney }) {
  const isIncoming = tx.type === "payment_in";
  const isPayout = tx.type === "payout_to_worker";
  const isCommission = tx.type === "commission";
  const isRefund = tx.type === "refund";

  let icon, label, color;
  if (isIncoming) {
    icon = "↓";
    label = `Payment from ${tx.client}`;
    color = "#2A8A8A";
  } else if (isPayout) {
    icon = "↑";
    label = `Payout to worker ${tx.worker}`;
    color = "var(--text)";
  } else if (isCommission) {
    icon = "★";
    label = "Platform commission";
    color = "#C9A961";
  } else if (isRefund) {
    icon = "↩";
    label = `Refund to ${tx.client}`;
    color = "#D85A30";
  }

  return (
    <div style={styles.transactionRow}>
      <div style={{ ...styles.txIcon, color }}>{icon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={styles.txLabel}>{label}</div>
        <div style={styles.txMeta}>
          #{tx.id} · {tx.method} · {tx.time}
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ ...styles.txAmount, color }}>
          {tx.amount > 0 ? "+" : ""}
          {formatMoney(tx.amount)} UZS
        </div>
        <div
          style={{
            ...styles.txStatus,
            color: tx.status === "completed" ? "#2A8A8A" : "#C9A961",
          }}
        >
          {tx.status}
        </div>
      </div>
    </div>
  );
}

// =====================================================
// STYLES
// =====================================================

const tooltipStyle = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 13,
};

const styles = {
  demoBanner: {
    background: "rgba(201,169,97,0.12)",
    color: "#8a6f30",
    padding: "10px 14px",
    borderRadius: 8,
    fontSize: 12,
    marginBottom: 14,
    border: "1px solid rgba(201,169,97,0.3)",
    fontFamily: "system-ui, sans-serif",
  },
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
  periodSelector: {
    display: "flex",
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    overflow: "hidden",
  },
  periodBtn: {
    padding: "7px 14px",
    background: "var(--card)",
    border: "none",
    fontSize: 12,
    fontWeight: 500,
    color: "var(--text-muted)",
    cursor: "pointer",
    transition: "all 0.15s",
  },
  periodBtnActive: {
    background: "#2A8A8A",
    color: "#fff",
  },
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 12,
    marginBottom: 14,
  },
  kpiCard: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "16px 18px",
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
    minHeight: 92,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  kpiHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  kpiLabel: {
    fontSize: 12,
    color: "var(--text-faint)",
    fontWeight: 500,
  },
  kpiIcon: {
    fontSize: 16,
    opacity: 0.6,
  },
  kpiValue: {
    fontSize: 22,
    fontWeight: 600,
    color: "var(--text)",
    marginTop: 6,
    lineHeight: 1.1,
  },
  kpiAccent: {
    fontSize: 11,
    fontWeight: 500,
    marginTop: 4,
  },
  chartsRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
    marginBottom: 12,
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
  tableCard: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "16px 18px",
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  },
  thRow: {
    borderBottom: "1px solid var(--border)",
  },
  th: {
    padding: "8px 0",
    textAlign: "left",
    fontSize: 10,
    fontWeight: 600,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  tr: {
    borderBottom: "1px solid var(--border-subtle)",
  },
  td: {
    padding: "10px 0",
    color: "var(--text)",
    verticalAlign: "middle",
  },
  workerCell: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontWeight: 500,
  },
  rankBadge: {
    width: 22,
    height: 22,
    background: "#2A8A8A",
    color: "#fff",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 10,
    fontWeight: 700,
    flexShrink: 0,
  },
  transactionsCard: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "16px 18px",
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  transactionsList: {
    display: "flex",
    flexDirection: "column",
  },
  transactionRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 0",
    borderBottom: "1px solid var(--border-subtle)",
  },
  txIcon: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "var(--surface-2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
    fontWeight: 600,
    flexShrink: 0,
  },
  txLabel: {
    fontSize: 13,
    color: "var(--text)",
    fontWeight: 500,
  },
  txMeta: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 2,
  },
  txAmount: {
    fontSize: 14,
    fontWeight: 600,
  },
  txStatus: {
    fontSize: 10,
    textTransform: "uppercase",
    marginTop: 2,
    letterSpacing: 0.4,
    fontWeight: 600,
  },
};