// src/pages/AnalyticsPage.jsx
import { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

import KpiCard from "../components/KpiCard";
import {
  fetchAnalyticsKpis,
  fetchAnalyticsFunnel,
  fetchAnalyticsClientsTrend,
  fetchAnalyticsSupplyDemand,
} from "../api/analytics";

// ---- palette (matches the dashboard) ----
const NAVY = "#1A2B4A";
const TEAL = "#2A8A8A";
const STATUS_COLOR = { ok: "#3BA776", tight: "#E0A93B", gap: "#D85A30" };
const STATUS_LABEL = { ok: "OK", tight: "Tight", gap: "Gap" };

// ---- helpers ----
function isoDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
function todayIso() {
  return new Date().toISOString().slice(0, 10);
}
function formatMoney(n) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return `${Math.round(n)}`;
}
function formatDuration(sec) {
  if (!sec || sec <= 0) return "0m";
  if (sec >= 86400) return `${(sec / 86400).toFixed(1)}d`;
  if (sec >= 3600) return `${(sec / 3600).toFixed(1)}h`;
  return `${Math.round(sec / 60)}m`;
}
// delta accent text + color; higherIsBetter flips the good/bad coloring
function deltaAccent(deltaPct, higherIsBetter = true) {
  if (deltaPct == null) return { text: "no prior data", color: "var(--text-faint)" };
  const up = deltaPct >= 0;
  const good = higherIsBetter ? up : !up;
  const arrow = up ? "▲" : "▼";
  return {
    text: `${arrow} ${Math.abs(deltaPct).toFixed(1)}% vs prev`,
    color: good ? "#3BA776" : "#D85A30",
  };
}

export default function AnalyticsPage() {
  const [from, setFrom] = useState(isoDaysAgo(90));
  const [to, setTo] = useState(todayIso());
  const [district, setDistrict] = useState("");
  const [districtOptions, setDistrictOptions] = useState([]);

  const [kpis, setKpis] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [trend, setTrend] = useState(null);
  const [supply, setSupply] = useState(null);

  const [loading, setLoading] = useState({ kpis: true, funnel: true, trend: true, supply: true });
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const filters = { from, to, district };
    setLoading({ kpis: true, funnel: true, trend: true, supply: true });
    setError(null);

    fetchAnalyticsKpis(filters)
      .then((d) => !cancelled && setKpis(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading((l) => ({ ...l, kpis: false })));

    fetchAnalyticsFunnel(filters)
      .then((d) => !cancelled && setFunnel(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading((l) => ({ ...l, funnel: false })));

    fetchAnalyticsClientsTrend(filters)
      .then((d) => !cancelled && setTrend(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading((l) => ({ ...l, trend: false })));

    fetchAnalyticsSupplyDemand(filters)
      .then((d) => {
        if (cancelled) return;
        setSupply(d);
        // Populate the district dropdown from the unfiltered result only.
        if (!district && d.districts?.length) setDistrictOptions(d.districts);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading((l) => ({ ...l, supply: false })));

    return () => { cancelled = true; };
  }, [from, to, district]);

  const k = kpis?.kpis;

  return (
    <div>
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.pageTitle}>Analytics</h2>
          <p style={styles.pageSub}>Trends, funnel & supply/demand over a date range</p>
        </div>
        <div style={styles.filters}>
          <label style={styles.filterLabel}>
            From
            <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} style={styles.input} />
          </label>
          <label style={styles.filterLabel}>
            To
            <input type="date" value={to} min={from} max={todayIso()} onChange={(e) => setTo(e.target.value)} style={styles.input} />
          </label>
          <label style={styles.filterLabel}>
            District
            <select value={district} onChange={(e) => setDistrict(e.target.value)} style={styles.input}>
              <option value="">All districts</option>
              {districtOptions.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>Failed to load analytics: {error}</div>}

      {/* KPI row */}
      <div style={styles.kpiGrid}>
        <KpiCard label="GMV" value={loading.kpis ? "" : formatMoney(k?.gmv?.value)} loading={loading.kpis}
          accent={k && deltaAccent(k.gmv.delta_pct).text} accentColor={k && deltaAccent(k.gmv.delta_pct).color} />
        <KpiCard label="Fill rate" value={loading.kpis ? "" : `${k?.fill_rate?.value ?? 0}%`} loading={loading.kpis}
          accent={k && deltaAccent(k.fill_rate.delta_pct).text} accentColor={k && deltaAccent(k.fill_rate.delta_pct).color} />
        <KpiCard label="Avg time to assign" value={loading.kpis ? "" : formatDuration(k?.avg_time_to_assign?.value)} loading={loading.kpis}
          accent={k && deltaAccent(k.avg_time_to_assign.delta_pct, false).text} accentColor={k && deltaAccent(k.avg_time_to_assign.delta_pct, false).color} />
        <KpiCard label="Repeat client rate" value={loading.kpis ? "" : `${k?.repeat_client_rate?.value ?? 0}%`} loading={loading.kpis}
          accent={k && deltaAccent(k.repeat_client_rate.delta_pct).text} accentColor={k && deltaAccent(k.repeat_client_rate.delta_pct).color} />
      </div>

      {/* Funnel + Clients trend */}
      <div style={styles.chartsRow}>
        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>Order funnel</h3>
            <span style={styles.chartSubtitle}>created → assigned → accepted → completed</span>
          </div>
          {loading.funnel ? <Centered>Loading…</Centered> : <Funnel data={funnel} />}
        </div>

        <div style={styles.chartCard}>
          <div style={styles.chartHeader}>
            <h3 style={styles.chartTitle}>New vs returning clients</h3>
            <span style={styles.chartSubtitle}>Weekly</span>
          </div>
          <div style={{ width: "100%", height: 260 }}>
            {loading.trend ? (
              <Centered>Loading…</Centered>
            ) : !trend?.weeks?.length ? (
              <Centered>No client activity in this range</Centered>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend.weeks} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
                  <XAxis dataKey="week" stroke="#888" fontSize={11} tickLine={false} />
                  <YAxis stroke="#888" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="new" name="New" stackId="1" stroke={TEAL} fill={TEAL} fillOpacity={0.75} />
                  <Area type="monotone" dataKey="returning" name="Returning" stackId="1" stroke={NAVY} fill={NAVY} fillOpacity={0.6} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Supply / demand heatmap */}
      <div style={styles.chartCard}>
        <div style={styles.chartHeader}>
          <h3 style={styles.chartTitle}>Supply / demand by district × profession</h3>
          <Legend2 />
        </div>
        {loading.supply ? <Centered>Loading…</Centered> : <Heatmap data={supply} />}
      </div>
    </div>
  );
}

// ---------- sub-components ----------
function Centered({ children }) {
  return <div style={styles.centered}>{children}</div>;
}

function Funnel({ data }) {
  const primary = data?.primary || [];
  const maxCount = primary[0]?.count || 0;
  if (!maxCount) return <Centered>No orders in this range</Centered>;
  return (
    <div>
      {primary.map((s, i) => (
        <div key={s.stage} style={{ marginBottom: 10 }}>
          <div style={styles.funnelLabelRow}>
            <span style={styles.funnelStage}>{s.stage}</span>
            <span style={styles.funnelCount}>
              {s.count} · {s.pct_of_created}%
              {i > 0 && s.dropoff_pct > 0 && (
                <span style={styles.dropoff}> (−{s.dropoff_pct}%)</span>
              )}
            </span>
          </div>
          <div style={styles.funnelTrack}>
            <div style={{ ...styles.funnelBar, width: `${maxCount ? (s.count / maxCount) * 100 : 0}%` }} />
          </div>
        </div>
      ))}
      {data?.secondary?.length > 0 && (
        <div style={styles.secondaryBox}>
          <div style={styles.secondaryTitle}>Application funnel (workers → jobs)</div>
          <div style={styles.secondaryRow}>
            {data.secondary.map((s) => (
              <span key={s.stage} style={styles.secondaryChip}>
                {s.stage}: <strong>{s.count}</strong> ({s.pct_of_applied}%)
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Legend2() {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      {["ok", "tight", "gap"].map((s) => (
        <span key={s} style={styles.legendItem}>
          <span style={{ ...styles.legendSwatch, background: STATUS_COLOR[s] }} />
          {STATUS_LABEL[s]}
        </span>
      ))}
    </div>
  );
}

function Heatmap({ data }) {
  const districts = data?.districts || [];
  const professions = data?.professions || [];
  const cellMap = useMemo(() => {
    const m = {};
    (data?.cells || []).forEach((c) => { m[`${c.district}|${c.profession}`] = c; });
    return m;
  }, [data]);

  if (!districts.length || !professions.length) {
    return <Centered>No supply/demand data for this range</Centered>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ display: "grid", gridTemplateColumns: `150px repeat(${professions.length}, minmax(90px, 1fr))`, gap: 4, minWidth: 150 + professions.length * 90 }}>
        <div style={styles.hmCorner} />
        {professions.map((p) => (
          <div key={p} style={styles.hmColHead} title={p}>{p}</div>
        ))}
        {districts.map((dist) => (
          <FragmentRow key={dist} dist={dist} professions={professions} cellMap={cellMap} />
        ))}
      </div>
    </div>
  );
}

function FragmentRow({ dist, professions, cellMap }) {
  return (
    <>
      <div style={styles.hmRowHead} title={dist}>{dist}</div>
      {professions.map((p) => {
        const c = cellMap[`${dist}|${p}`];
        const status = c?.status || "ok";
        return (
          <div
            key={p}
            style={{ ...styles.hmCell, background: STATUS_COLOR[status] }}
            title={`${dist} · ${p}\nDemand: ${c?.demand ?? 0}\nMasters: ${c?.available_masters ?? 0}\nStatus: ${STATUS_LABEL[status]}`}
          >
            {c ? `${c.demand}/${c.available_masters}` : "0/0"}
          </div>
        );
      })}
    </>
  );
}

// ---------- styles ----------
const tooltipStyle = { background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13 };

const styles = {
  headerRow: { display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 16, flexWrap: "wrap", gap: 12 },
  pageTitle: { margin: 0, fontSize: 20, fontWeight: 600, color: NAVY },
  pageSub: { margin: "4px 0 0", fontSize: 13, color: "var(--text-faint)" },
  filters: { display: "flex", gap: 10, alignItems: "flex-end" },
  filterLabel: { display: "flex", flexDirection: "column", gap: 4, fontSize: 11, color: "var(--text-faint)", fontWeight: 500 },
  input: { padding: "7px 10px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, color: NAVY, background: "var(--card)" },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 },
  chartsRow: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 },
  chartCard: { background: "var(--card)", borderRadius: 10, padding: "16px 18px", border: "1px solid var(--border)", fontFamily: "system-ui, sans-serif", marginBottom: 12 },
  chartHeader: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 },
  chartTitle: { margin: 0, fontSize: 14, fontWeight: 600, color: NAVY },
  chartSubtitle: { fontSize: 11, color: "var(--text-faint)" },
  errorBanner: { background: "rgba(216,90,48,0.08)", color: "#D85A30", padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, border: "1px solid rgba(216,90,48,0.2)" },
  centered: { display: "flex", alignItems: "center", justifyContent: "center", height: 240, color: "var(--text-faint)", fontSize: 13 },
  // funnel
  funnelLabelRow: { display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 },
  funnelStage: { color: NAVY, fontWeight: 600, textTransform: "capitalize" },
  funnelCount: { color: "#555" },
  dropoff: { color: "#D85A30", fontWeight: 600 },
  funnelTrack: { background: "#F0F2F5", borderRadius: 6, height: 22, overflow: "hidden" },
  funnelBar: { background: TEAL, height: "100%", borderRadius: 6, transition: "width .3s" },
  secondaryBox: { marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border-subtle)" },
  secondaryTitle: { fontSize: 11, color: "var(--text-faint)", fontWeight: 600, marginBottom: 6 },
  secondaryRow: { display: "flex", gap: 10, flexWrap: "wrap" },
  secondaryChip: { fontSize: 12, color: NAVY, background: "#F6F8FA", borderRadius: 6, padding: "4px 8px" },
  // legend
  legendItem: { display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "#555" },
  legendSwatch: { width: 12, height: 12, borderRadius: 3, display: "inline-block" },
  // heatmap
  hmCorner: { height: 34 },
  hmColHead: { fontSize: 11, fontWeight: 600, color: NAVY, padding: "6px 4px", textAlign: "center", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  hmRowHead: { fontSize: 12, color: NAVY, fontWeight: 500, display: "flex", alignItems: "center", paddingRight: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  hmCell: { height: 38, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "default" },
};
