import { useState } from "react";
import { Users, Plus } from "lucide-react";
import { api } from "../api/client";
import { MOCK } from "../mocks/data";
import { useFetch } from "../hooks/useFetch";
import { fmt, inputStyle, btnPrimary } from "../utils/helpers";
import { StatusBadge, EmptyState, Toast, Spinner, Modal, FormField } from "../components/ui";

// ── Create Advertiser Modal ─────────────────────────────────────
function CreateAdvertiserModal({ onClose, onSubmit }) {
  const [form, setForm] = useState({ advertiser_id: "", name: "", company_name: "", contact_email: "", billing_email: "" });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const btnSecondary = {
    padding: "10px 22px", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8",
    transition: "all 0.2s",
  };
  return (
    <Modal title="New Advertiser" onClose={onClose}>
      <FormField label="Advertiser ID"><input style={inputStyle} value={form.advertiser_id} onChange={e => set("advertiser_id", e.target.value)} placeholder="adv_company" /></FormField>
      <FormField label="Name"><input style={inputStyle} value={form.name} onChange={e => set("name", e.target.value)} placeholder="Company Name" /></FormField>
      <FormField label="Company Name"><input style={inputStyle} value={form.company_name} onChange={e => set("company_name", e.target.value)} placeholder="Legal entity name" /></FormField>
      <FormField label="Contact Email"><input style={inputStyle} type="email" value={form.contact_email} onChange={e => set("contact_email", e.target.value)} placeholder="ads@company.com" /></FormField>
      <FormField label="Billing Email"><input style={inputStyle} type="email" value={form.billing_email} onChange={e => set("billing_email", e.target.value)} placeholder="billing@company.com" /></FormField>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
        <button style={btnPrimary} onClick={() => onSubmit(form)}>Create Advertiser</button>
      </div>
    </Modal>
  );
}

// ── Advertisers Page ────────────────────────────────────────────
export function AdvertisersPage({ navigate }) {
  const [filter, setFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [toast, setToast] = useState(null);

  const { data: advertisers, loading, reload } = useFetch(
    () => api.get(`/portal/advertisers?limit=100`).catch(() => MOCK.advertisers),
    []
  );

  const filtered = (advertisers || []).filter(a => filter === "all" || a.status === filter);

  const handleCreate = async (form) => {
    try {
      await api.post("/portal/advertisers", form);
      setShowCreate(false);
      setToast({ message: "Advertiser created", type: "success" });
      reload();
    } catch (e) {
      setToast({ message: e.message, type: "error" });
    }
  };

  return (
    <div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0, letterSpacing: "-0.02em" }}>Advertisers</h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>Manage advertiser accounts</p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <select value={filter} onChange={e => setFilter(e.target.value)} style={{
            ...inputStyle, width: "auto", padding: "8px 12px", fontSize: 12, borderRadius: 8,
          }}>
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
          <button style={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={14} /> New Advertiser
          </button>
        </div>
      </div>

      {loading ? <Spinner /> : filtered.length === 0 ? (
        <EmptyState icon={Users} title="No advertisers" desc="Create your first advertiser to get started." action="New Advertiser" onAction={() => setShowCreate(true)} />
      ) : (
        <div style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 12, overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {["Name", "Company", "Status", "Contact Email", "Created"].map(h => (
                  <th key={h} style={{
                    padding: "12px 18px", textAlign: "left", fontSize: 11, fontWeight: 600,
                    color: "#64748b", letterSpacing: "0.05em", textTransform: "uppercase",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((a, i) => (
                <tr key={a.advertiser_id}
                  onClick={() => navigate("advertiser", { advertiserId: a.advertiser_id })}
                  style={{
                    borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer",
                    background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)"}
                >
                  <td style={{ padding: "14px 18px", color: "#e2e8f0", fontWeight: 500 }}>{a.name}</td>
                  <td style={{ padding: "14px 18px", color: "#94a3b8" }}>{a.company_name || "—"}</td>
                  <td style={{ padding: "14px 18px" }}><StatusBadge status={a.status} /></td>
                  <td style={{ padding: "14px 18px", color: "#94a3b8" }}>{a.contact_email}</td>
                  <td style={{ padding: "14px 18px", color: "#64748b" }}>{fmt.date(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateAdvertiserModal onClose={() => setShowCreate(false)} onSubmit={handleCreate} />
      )}
    </div>
  );
}