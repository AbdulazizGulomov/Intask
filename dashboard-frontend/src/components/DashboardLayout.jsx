// src/components/DashboardLayout.jsx
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function DashboardLayout() {
  return (
    <div style={styles.shell}>
      <Sidebar />
      <div style={styles.main}>
        <TopBar />
        <main style={styles.content}>
          {/* <Outlet /> renders whichever child route is active */}
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// ===== Inline styles =====
const styles = {
  shell: {
    display: "flex",
    minHeight: "100vh",
    background: "var(--bg)",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minWidth: 0, // prevents flex children from overflowing
  },
  content: {
    flex: 1,
    padding: "24px",
    overflowY: "auto",
  },
};