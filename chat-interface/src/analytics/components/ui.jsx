import { useState, useEffect } from "react";
import {
  Plus, X, Loader2, AlertCircle, Check
} from "lucide-react";
import { statusColor, inputStyle, fmt } from "../utils/helpers";

// ── StatusBadge ─────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const s = statusColor[status] || statusColor.draft;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", fontSize: 11, fontWeight: 600,
      textTransform: "uppercase", letterSpacing: "0.05em", padding: "3px 10px",
      borderRadius: 999, background: s.bg, color: s.text, border: `1px solid ${s.border}`,
    }}>
      {status}
    </span>
  );
}

// ── KPICard ─────────────────────────────────────────────────────
export function KPICard({ icon: Icon, label, value, sub, accent }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 12, padding: "20px 22px", flex: "1 1 0", minWidth: 160,
      transition: "border-color 0.2s, background 0.2s",
    }}
    onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.14)"; e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
    onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)"; e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: accent ? "rgba(245,158,11,0.1)" : "rgba(255,255,255,0.06)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon size={16} color={accent ? "#f59e0b" : "#94a3b8"} />
        </div>
        <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 500, letterSpacing: "0.02em" }}>{label}</span>
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em" }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ── TimeRangeSelector ───────────────────────────────────────────
export function TimeRangeSelector({ value, onChange }) {
  const opts = [7, 14, 30, 60, 90];
  return (
    <div style={{ display: "flex", gap: 4, background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: 3 }}>
      {opts.map(d => (
        <button key={d} onClick={() => onChange(d)} style={{
          padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 500, border: "none",
          cursor: "pointer", transition: "all 0.2s",
          background: value === d ? "rgba(245,158,11,0.15)" : "transparent",
          color: value === d ? "#f59e0b" : "#94a3b8",
        }}>
          {d}d
        </button>
      ))}
    </div>
  );
}

// ── BudgetBar ───────────────────────────────────────────────────
export function BudgetBar({ spent, total }) {
  const pct = total > 0 ? Math.min((spent / total) * 100, 100) : 0;
  const color = pct > 90 ? "#f87171" : pct > 70 ? "#f59e0b" : "#34d399";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
        <span>{fmt.money(spent)} spent</span>
        <span>{pct.toFixed(1)}% of {fmt.money(total)}</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, borderRadius: 3, background: color, transition: "width 0.5s ease" }} />
      </div>
    </div>
  );
}

// ── EmptyState ──────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, desc, action, onAction }) {
  return (
    <div style={{ textAlign: "center", padding: "60px 24px" }}>
      <div style={{
        width: 56, height: 56, borderRadius: 16, background: "rgba(255,255,255,0.04)",
        display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
      }}>
        <Icon size={24} color="#64748b" />
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: 13, color: "#64748b", marginBottom: 20, maxWidth: 340, margin: "0 auto 20px" }}>{desc}</div>
      {action && (
        <button onClick={onAction} style={{
          padding: "10px 20px", borderRadius: 8, border: "1px solid rgba(245,158,11,0.3)",
          background: "rgba(245,158,11,0.1)", color: "#f59e0b", fontSize: 13, fontWeight: 600,
          cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6,
        }}>
          <Plus size={14} /> {action}
        </button>
      )}
    </div>
  );
}

// ── Toast ────────────────────────────────────────────────────────
export function Toast({ message, type = "error", onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 5000); return () => clearTimeout(t); }, []);
  const bg = type === "error" ? "rgba(248,113,113,0.15)" : "rgba(52,211,153,0.15)";
  const border = type === "error" ? "rgba(248,113,113,0.3)" : "rgba(52,211,153,0.3)";
  const color = type === "error" ? "#f87171" : "#34d399";
  return (
    <div style={{
      position: "fixed", top: 20, right: 20, zIndex: 1000, padding: "12px 20px",
      borderRadius: 10, background: bg, border: `1px solid ${border}`, color,
      fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 8,
      backdropFilter: "blur(12px)", animation: "slideIn 0.3s ease",
    }}>
      {type === "error" ? <AlertCircle size={16} /> : <Check size={16} />}
      {message}
      <button onClick={onClose} style={{ marginLeft: 8, cursor: "pointer", background: "none", border: "none", color, padding: 0 }}>
        <X size={14} />
      </button>
    </div>
  );
}

// ── Spinner ─────────────────────────────────────────────────────
export function Spinner() {
  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: 60 }}>
      <Loader2 size={28} color="#f59e0b" style={{ animation: "spin 1s linear infinite" }} />
    </div>
  );
}

// ── Modal ────────────────────────────────────────────────────────
export function Modal({ title, onClose, children, width = 520 }) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 999, display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)", animation: "fadeIn 0.15s ease",
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        width, maxWidth: "90vw", maxHeight: "85vh", overflow: "auto",
        background: "#141418", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 14, padding: "28px 32px",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{
            width: 30, height: 30, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(255,255,255,0.06)", border: "none", cursor: "pointer", color: "#94a3b8",
          }}>
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ── FormField ───────────────────────────────────────────────────
export function FormField({ label, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#94a3b8", marginBottom: 6, letterSpacing: "0.02em" }}>{label}</label>
      {children}
    </div>
  );
}

// ── TagInput ────────────────────────────────────────────────────
export function TagInput({ value = [], onChange, placeholder }) {
  const [input, setInput] = useState("");
  const add = () => {
    const v = input.trim();
    if (v && !value.includes(v)) { onChange([...value, v]); setInput(""); }
  };
  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: value.length ? 8 : 0 }}>
        {value.map((t, i) => (
          <span key={i} style={{
            display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 10px",
            borderRadius: 6, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)",
            fontSize: 12, color: "#f59e0b", fontWeight: 500,
          }}>
            {t}
            <button onClick={() => onChange(value.filter((_, j) => j !== i))} style={{
              background: "none", border: "none", cursor: "pointer", padding: 0, color: "#f59e0b", display: "flex",
            }}>
              <X size={12} />
            </button>
          </span>
        ))}
      </div>
      <input
        style={inputStyle} value={input} placeholder={placeholder || "Type and press Enter"}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
      />
    </div>
  );
}

// ── LegendItem ──────────────────────────────────────────────────
export function LegendItem({ color, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#94a3b8" }}>
      <span style={{ width: 10, height: 3, borderRadius: 2, background: color }} />
      {label}
    </div>
  );
}