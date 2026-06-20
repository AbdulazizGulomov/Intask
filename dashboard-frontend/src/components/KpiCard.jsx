// src/components/KpiCard.jsx
export default function KpiCard({
  label,
  value,
  accent,
  accentColor = "#2A8A8A",
  loading = false,
  icon = null,
}) {
  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={styles.label}>{label}</span>
        {icon && <span style={styles.icon}>{icon}</span>}
      </div>

      {loading ? (
        <div style={styles.skeleton} />
      ) : (
        <>
          <div style={styles.value}>{value}</div>
          {accent && (
            <div style={{ ...styles.accent, color: accentColor }}>
              {accent}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ===== Inline styles =====
const styles = {
  card: {
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
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    fontSize: 12,
    color: "var(--text-faint)",
    fontWeight: 500,
  },
  icon: {
    fontSize: 16,
    opacity: 0.5,
  },
  value: {
    fontSize: 26,
    fontWeight: 600,
    color: "var(--text)",
    marginTop: 6,
    lineHeight: 1.1,
  },
  accent: {
    fontSize: 11,
    fontWeight: 500,
    marginTop: 4,
  },
  skeleton: {
    height: 32,
    width: "60%",
    background: "linear-gradient(90deg, var(--surface-2) 25%, var(--surface-3) 50%, var(--surface-2) 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.5s infinite",
    borderRadius: 4,
    marginTop: 6,
  },
};