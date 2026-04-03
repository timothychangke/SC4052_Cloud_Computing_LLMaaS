// ── Formatters ──────────────────────────────────────────────────
export const fmt = {
  num: (n) => n != null ? n.toLocaleString("en-US") : "—",
  money: (n) => n != null ? `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—",
  pct: (n) => n != null ? `${(n * 100).toFixed(2)}%` : "—",
  date: (s) => {
    if (!s) return "—";
    const d = new Date(s);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  },
  shortDate: (s) => {
    if (!s) return "";
    const d = new Date(s);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  },
};

// ── CTR color helper ────────────────────────────────────────────
export const ctrColor = (ctr) => {
  if (ctr > 0.03) return "#34d399";
  if (ctr > 0.01) return "#f59e0b";
  return "#f87171";
};

export const scoreColor = (score) => {
  if (score >= 0.7) return "#34d399";
  if (score >= 0.4) return "#f59e0b";
  return "#f87171";
};

// ── Status color map ────────────────────────────────────────────
export const statusColor = {
  active: { bg: "rgba(52,211,153,0.12)", text: "#34d399", border: "rgba(52,211,153,0.25)" },
  draft: { bg: "rgba(148,163,184,0.12)", text: "#94a3b8", border: "rgba(148,163,184,0.25)" },
  paused: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b", border: "rgba(245,158,11,0.25)" },
  completed: { bg: "rgba(96,165,250,0.12)", text: "#60a5fa", border: "rgba(96,165,250,0.25)" },
  suspended: { bg: "rgba(248,113,113,0.12)", text: "#f87171", border: "rgba(248,113,113,0.25)" },
};

// ── Shared inline styles ────────────────────────────────────────
export const inputStyle = {
  width: "100%", padding: "10px 14px", borderRadius: 8, fontSize: 14,
  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
  color: "#f1f5f9", outline: "none", fontFamily: "inherit", boxSizing: "border-box",
};

export const btnPrimary = {
  padding: "10px 22px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer",
  background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b",
  display: "inline-flex", alignItems: "center", gap: 6, transition: "all 0.2s",
};

export const btnSecondary = {
  padding: "10px 22px", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8",
  transition: "all 0.2s",
};

// ── Chart tooltip style ─────────────────────────────────────────
export const chartTooltipStyle = {
  contentStyle: {
    background: "#1a1a22", border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 10, padding: "10px 14px", fontSize: 12, color: "#e2e8f0",
  },
  labelStyle: { color: "#94a3b8", fontWeight: 600, marginBottom: 4 },
};