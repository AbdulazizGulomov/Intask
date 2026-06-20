// src/pages/SettingsPage.jsx
import { useEffect, useState } from "react";
import {
  fetchSettingsProfile,
  updateSettingsProfile,
  changePassword,
  listOperators,
  createOperator,
  setOperatorActive,
} from "../api/dashboard";
import { useAuth } from "../auth/AuthContext";

export default function SettingsPage() {
  const { isAdmin } = useAuth();

  return (
    <div>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Settings</h2>
          <p style={styles.subtitle}>
            Manage your account and dashboard preferences
          </p>
        </div>
      </div>

      <div style={styles.sections}>
        <ProfileSection />
        <PasswordSection />
        {/* Operator Management is admin-only — hidden entirely for non-admins */}
        {isAdmin && <OperatorsSection />}
        <PreferencesSection />
      </div>
    </div>
  );
}

// =====================================================
// SECTION 1 — MY PROFILE
// =====================================================
function ProfileSection() {
  const [profile, setProfile] = useState(null);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchSettingsProfile()
      .then((data) => {
        if (cancelled) return;
        setProfile(data);
        setUsername(data.username || "");
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.response?.data?.detail || err.message || "Failed to load profile");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = profile && username.trim() !== (profile.username || "");

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await updateSettingsProfile({ username: username.trim() });
      setProfile(updated);
      setUsername(updated.username || "");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2500);
    } catch (err) {
      const data = err.response?.data;
      setError(
        data?.username?.[0] ||
          data?.detail ||
          err.message ||
          "Failed to save profile"
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section style={styles.card}>
      <div style={styles.cardHead}>
        <div>
          <h3 style={styles.cardTitle}>My Profile</h3>
          <p style={styles.cardSub}>Phone and role are fixed. You can update your display name.</p>
        </div>
        <span style={styles.cardIcon}>👤</span>
      </div>

      {loading ? (
        <div style={styles.loading}>Loading profile…</div>
      ) : (
        <form onSubmit={handleSave}>
          <div style={styles.fieldGrid}>
            {/* Read-only: phone */}
            <div style={styles.field}>
              <label style={styles.label}>Phone</label>
              <input
                type="text"
                value={profile?.phone || "—"}
                readOnly
                disabled
                style={{ ...styles.input, ...styles.inputReadonly }}
              />
              <span style={styles.hint}>Read-only · login identifier</span>
            </div>

            {/* Read-only: role */}
            <div style={styles.field}>
              <label style={styles.label}>Role</label>
              <input
                type="text"
                value={
                  profile?.role
                    ? profile.role.charAt(0).toUpperCase() + profile.role.slice(1)
                    : "—"
                }
                readOnly
                disabled
                style={{ ...styles.input, ...styles.inputReadonly }}
              />
              <span style={styles.hint}>Read-only</span>
            </div>

            {/* Editable: username / display name */}
            <div style={{ ...styles.field, gridColumn: "1 / -1" }}>
              <label style={styles.label}>Display name (username)</label>
              <input
                type="text"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  setSuccess(false);
                }}
                placeholder="Enter a display name"
                style={styles.input}
              />
            </div>
          </div>

          {error && <div style={styles.errorBanner}>{error}</div>}
          {success && <div style={styles.successBanner}>✓ Profile saved</div>}

          <div style={styles.actions}>
            <button
              type="submit"
              disabled={!dirty || saving || !username.trim()}
              style={{
                ...styles.btnPrimary,
                opacity: !dirty || saving || !username.trim() ? 0.5 : 1,
                cursor: !dirty || saving || !username.trim() ? "not-allowed" : "pointer",
              }}
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

// =====================================================
// SECTION 2 — CHANGE PASSWORD
// =====================================================
function PasswordSection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const canSubmit = current && next && confirm && !saving;

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await changePassword({
        current_password: current,
        new_password: next,
        confirm,
      });
      setSuccess(true);
      setCurrent("");
      setNext("");
      setConfirm("");
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      const data = err.response?.data;
      // Surface the most specific field error the API returned
      const msg =
        data?.current_password?.[0] ||
        data?.new_password?.[0] ||
        data?.confirm?.[0] ||
        data?.detail ||
        err.message ||
        "Failed to change password";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section style={styles.card}>
      <div style={styles.cardHead}>
        <div>
          <h3 style={styles.cardTitle}>Change Password</h3>
          <p style={styles.cardSub}>
            Update the password you use to sign in to the dashboard.
          </p>
        </div>
        <span style={styles.cardIcon}>🔒</span>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={styles.fieldGrid}>
          <div style={{ ...styles.field, gridColumn: "1 / -1" }}>
            <label style={styles.label}>Current password</label>
            <input
              type="password"
              value={current}
              onChange={(e) => {
                setCurrent(e.target.value);
                setSuccess(false);
              }}
              autoComplete="current-password"
              placeholder="Enter current password"
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>New password</label>
            <input
              type="password"
              value={next}
              onChange={(e) => {
                setNext(e.target.value);
                setSuccess(false);
              }}
              autoComplete="new-password"
              placeholder="Enter new password"
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Confirm new password</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => {
                setConfirm(e.target.value);
                setSuccess(false);
              }}
              autoComplete="new-password"
              placeholder="Re-enter new password"
              style={styles.input}
            />
          </div>
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}
        {success && <div style={styles.successBanner}>✓ Password changed</div>}

        <div style={styles.actions}>
          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              ...styles.btnPrimary,
              opacity: canSubmit ? 1 : 0.5,
              cursor: canSubmit ? "pointer" : "not-allowed",
            }}
          >
            {saving ? "Updating…" : "Update password"}
          </button>
        </div>
      </form>
    </section>
  );
}

// =====================================================
// SECTION 3 — OPERATOR MANAGEMENT (admin-only)
// =====================================================
function OperatorsSection() {
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);

  // create form
  const [phone, setPhone] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [createSuccess, setCreateSuccess] = useState(false);

  // per-row toggle in-flight id
  const [togglingId, setTogglingId] = useState(null);

  function load() {
    setLoading(true);
    listOperators()
      .then((data) => {
        setOperators(Array.isArray(data) ? data : []);
        setListError(null);
      })
      .catch((err) => setListError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  const canCreate = phone.trim() && username.trim() && password && !creating;

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    setCreateSuccess(false);
    try {
      const op = await createOperator({
        phone: phone.trim(),
        username: username.trim(),
        password,
      });
      setOperators((prev) => [op, ...prev]);
      setPhone("");
      setUsername("");
      setPassword("");
      setCreateSuccess(true);
      setTimeout(() => setCreateSuccess(false), 3000);
    } catch (err) {
      const data = err.response?.data;
      setCreateError(
        data?.phone?.[0] ||
          data?.username?.[0] ||
          data?.password?.[0] ||
          data?.detail ||
          err.message ||
          "Failed to create operator"
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleToggle(op) {
    setTogglingId(op.id);
    try {
      const updated = await setOperatorActive(op.id, !op.is_active);
      setOperators((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
    } catch (err) {
      setListError(err.response?.data?.detail || err.message);
    } finally {
      setTogglingId(null);
    }
  }

  return (
    <section style={styles.card}>
      <div style={styles.cardHead}>
        <div>
          <h3 style={styles.cardTitle}>Operator Management</h3>
          <p style={styles.cardSub}>
            Admin-only. Create operator accounts and enable or disable their access.
          </p>
        </div>
        <span style={styles.cardIcon}>🛡️</span>
      </div>

      {/* Create operator */}
      <form onSubmit={handleCreate} style={styles.createForm}>
        <div style={styles.fieldGrid}>
          <div style={styles.field}>
            <label style={styles.label}>Phone</label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+998901234567"
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="operator2"
              style={styles.input}
            />
          </div>
          <div style={{ ...styles.field, gridColumn: "1 / -1" }}>
            <label style={styles.label}>Initial password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              placeholder="Set an initial password"
              style={styles.input}
            />
          </div>
        </div>

        {createError && <div style={styles.errorBanner}>{createError}</div>}
        {createSuccess && <div style={styles.successBanner}>✓ Operator created</div>}

        <div style={styles.actions}>
          <button
            type="submit"
            disabled={!canCreate}
            style={{
              ...styles.btnPrimary,
              opacity: canCreate ? 1 : 0.5,
              cursor: canCreate ? "pointer" : "not-allowed",
            }}
          >
            {creating ? "Creating…" : "Create operator"}
          </button>
        </div>
      </form>

      {/* Operator list */}
      <div style={styles.opListWrap}>
        {loading ? (
          <div style={styles.loading}>Loading operators…</div>
        ) : listError ? (
          <div style={styles.errorBanner}>{listError}</div>
        ) : operators.length === 0 ? (
          <div style={styles.loading}>No operators yet.</div>
        ) : (
          <table style={styles.opTable}>
            <thead>
              <tr style={styles.opThRow}>
                <th style={styles.opTh}>Operator</th>
                <th style={styles.opTh}>Phone</th>
                <th style={{ ...styles.opTh, textAlign: "center" }}>Status</th>
                <th style={{ ...styles.opTh, textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {operators.map((op) => (
                <tr key={op.id} style={styles.opTr}>
                  <td style={styles.opTd}>
                    <div style={{ fontWeight: 500 }}>{op.username || "—"}</div>
                    <div style={{ fontSize: 11, color: "var(--text-faint)" }}>#{op.id}</div>
                  </td>
                  <td style={{ ...styles.opTd, fontFamily: "monospace", fontSize: 12, color: "var(--text-muted)" }}>
                    {op.phone || "—"}
                  </td>
                  <td style={{ ...styles.opTd, textAlign: "center" }}>
                    <span
                      style={{
                        ...styles.statusPill,
                        background: op.is_active ? "rgba(42,138,138,0.12)" : "rgba(153,153,153,0.15)",
                        color: op.is_active ? "#2A8A8A" : "var(--text-faint)",
                      }}
                    >
                      {op.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td style={{ ...styles.opTd, textAlign: "right" }}>
                    <button
                      onClick={() => handleToggle(op)}
                      disabled={togglingId === op.id}
                      style={{
                        ...styles.toggleBtn,
                        color: op.is_active ? "#D85A30" : "#2A8A8A",
                        borderColor: op.is_active ? "rgba(216,90,48,0.4)" : "rgba(42,138,138,0.4)",
                        opacity: togglingId === op.id ? 0.5 : 1,
                      }}
                    >
                      {togglingId === op.id
                        ? "…"
                        : op.is_active
                        ? "Deactivate"
                        : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// =====================================================
// SECTION 4 — UI PREFERENCES (client-only, localStorage)
// =====================================================
const THEME_KEY = "intask_pref_theme";
const DENSITY_KEY = "intask_pref_density";

function PreferencesSection() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem(THEME_KEY) || "light"
  );
  const [density, setDensity] = useState(
    () => localStorage.getItem(DENSITY_KEY) || "comfortable"
  );

  // Persist + reflect on the document (harmless data-attributes; no backend)
  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(DENSITY_KEY, density);
    document.documentElement.setAttribute("data-density", density);
  }, [density]);

  return (
    <section style={styles.card}>
      <div style={styles.cardHead}>
        <div>
          <h3 style={styles.cardTitle}>UI Preferences</h3>
          <p style={styles.cardSub}>
            Saved on this device only — applied instantly, no account needed.
          </p>
        </div>
        <span style={styles.cardIcon}>🎨</span>
      </div>

      <div style={styles.prefRow}>
        <div>
          <div style={styles.prefLabel}>Theme</div>
          <div style={styles.prefHint}>Light or dark appearance</div>
        </div>
        <Segmented
          value={theme}
          onChange={setTheme}
          options={[
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
          ]}
        />
      </div>

      <div style={{ ...styles.prefRow, borderBottom: "none", paddingBottom: 0 }}>
        <div>
          <div style={styles.prefLabel}>Density</div>
          <div style={styles.prefHint}>Spacing of tables and lists</div>
        </div>
        <Segmented
          value={density}
          onChange={setDensity}
          options={[
            { value: "comfortable", label: "Comfortable" },
            { value: "compact", label: "Compact" },
          ]}
        />
      </div>
    </section>
  );
}

function Segmented({ value, onChange, options }) {
  return (
    <div style={styles.seg}>
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            style={{
              ...styles.segBtn,
              ...(active ? styles.segBtnActive : {}),
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// =====================================================
// STYLES (teal/navy theme, matches Finance/Clients pages)
// =====================================================
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
  sections: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    maxWidth: 760,
  },
  card: {
    background: "var(--card)",
    borderRadius: 10,
    padding: "18px 20px",
    border: "1px solid var(--border)",
    fontFamily: "system-ui, sans-serif",
  },
  cardHead: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  cardTitle: {
    margin: 0,
    fontSize: 15,
    fontWeight: 600,
    color: "var(--text)",
  },
  cardSub: {
    margin: "3px 0 0",
    fontSize: 12,
    color: "var(--text-faint)",
  },
  cardIcon: {
    fontSize: 18,
    opacity: 0.6,
  },
  loading: {
    padding: "20px 0",
    color: "var(--text-faint)",
    fontSize: 13,
  },
  fieldGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 14,
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 5,
  },
  label: {
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  input: {
    width: "100%",
    padding: "9px 12px",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 13,
    outline: "none",
    color: "var(--text)",
    background: "var(--card)",
    fontFamily: "inherit",
    boxSizing: "border-box",
  },
  inputReadonly: {
    background: "var(--surface-2)",
    color: "var(--text-faint)",
    cursor: "not-allowed",
  },
  hint: {
    fontSize: 11,
    color: "var(--text-faint-2)",
  },
  errorBanner: {
    background: "rgba(216,90,48,0.08)",
    color: "#D85A30",
    padding: "9px 12px",
    borderRadius: 8,
    fontSize: 12,
    marginTop: 14,
    border: "1px solid rgba(216,90,48,0.2)",
  },
  successBanner: {
    background: "rgba(42,138,138,0.1)",
    color: "#2A8A8A",
    padding: "9px 12px",
    borderRadius: 8,
    fontSize: 12,
    marginTop: 14,
    border: "1px solid rgba(42,138,138,0.25)",
    fontWeight: 500,
  },
  actions: {
    display: "flex",
    justifyContent: "flex-end",
    marginTop: 16,
  },
  btnPrimary: {
    padding: "9px 18px",
    background: "#2A8A8A",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    fontFamily: "inherit",
  },
  createForm: {
    paddingBottom: 16,
    marginBottom: 16,
    borderBottom: "1px solid var(--border-subtle)",
  },
  opListWrap: {
    overflow: "hidden",
  },
  opTable: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 13,
  },
  opThRow: {
    background: "var(--surface-2)",
    borderBottom: "1px solid var(--border)",
  },
  opTh: {
    padding: "8px 10px",
    textAlign: "left",
    fontSize: 10,
    fontWeight: 600,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  opTr: {
    borderBottom: "1px solid var(--border-subtle)",
  },
  opTd: {
    padding: "10px",
    color: "var(--text)",
    verticalAlign: "middle",
  },
  statusPill: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 20,
    fontSize: 11,
    fontWeight: 600,
  },
  toggleBtn: {
    padding: "5px 12px",
    background: "var(--card)",
    border: "1px solid",
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 500,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  prefRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 0",
    borderBottom: "1px solid var(--border-subtle)",
  },
  prefLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--text)",
  },
  prefHint: {
    fontSize: 11,
    color: "var(--text-faint)",
    marginTop: 2,
  },
  seg: {
    display: "flex",
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    overflow: "hidden",
  },
  segBtn: {
    padding: "7px 16px",
    background: "var(--card)",
    border: "none",
    fontSize: 12,
    fontWeight: 500,
    color: "var(--text-muted)",
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.15s",
  },
  segBtnActive: {
    background: "#2A8A8A",
    color: "#fff",
  },
};
