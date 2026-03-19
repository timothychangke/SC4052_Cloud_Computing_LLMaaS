import { useState } from "react";
import {
  ChevronRight, Plus, Pencil, Eye, MousePointerClick, TrendingUp, Target, Play
} from "lucide-react";
import { api } from "../api/client";
import { MOCK } from "../mocks/data";
import { useFetch } from "../hooks/useFetch";
import { fmt, inputStyle, btnPrimary, btnSecondary } from "../utils/helpers";
import {
  StatusBadge, KPICard, BudgetBar, EmptyState, Toast, Spinner, Modal, FormField
} from "../components/ui";

// ── Edit Advertiser Modal ───────────────────────────────────────
function EditAdvertiserModal({ adv, onClose, onSuccess, onError }) {
  const [form, setForm] = useState({
    name: adv?.name || "", company_name: adv?.company_name || "",
    contact_email: adv?.contact_email || "", billing_email: adv?.billing_email || "",
    status: adv?.status || "active",
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = async () => {
    try { await api.patch(`/portal/advertisers/${adv.advertiser_id}`, form); onSuccess(); } catch (e) { onError(e.message); }
  };
  return (
    <Modal title="Edit Advertiser" onClose={onClose}>
      <FormField label="Name"><input style={inputStyle} value={form.name} onChange={e => set("name", e.target.value)} /></FormField>
      <FormField label="Company Name"><input style={inputStyle} value={form.company_name} onChange={e => set("company_name", e.target.value)} /></FormField>
      <FormField label="Contact Email"><input style={inputStyle} value={form.contact_email} onChange={e => set("contact_email", e.target.value)} /></FormField>
      <FormField label="Billing Email"><input style={inputStyle} value={form.billing_email} onChange={e => set("billing_email", e.target.value)} /></FormField>
      <FormField label="Status">
        <select style={{ ...inputStyle, cursor: "pointer" }} value={form.status} onChange={e => set("status", e.target.value)}>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
      </FormField>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
        <button style={btnPrimary} onClick={submit}>Save Changes</button>
      </div>
    </Modal>
  );
}

// ── Create Campaign Modal ───────────────────────────────────────
function CreateCampaignModal({ advertiserId, onClose, onSuccess, onError }) {
  const [form, setForm] = useState({ name: "", total_budget: "", daily_budget: "", start_date: "", end_date: "" });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = async () => {
    try {
      const body = { name: form.name, total_budget: parseFloat(form.total_budget) || 0 };
      if (form.daily_budget) body.daily_budget = parseFloat(form.daily_budget);
      if (form.start_date) body.start_date = form.start_date;
      if (form.end_date) body.end_date = form.end_date;
      await api.post(`/portal/advertisers/${advertiserId}/campaigns`, body);
      onSuccess();
    } catch (e) { onError(e.message); }
  };
  return (
    <Modal title="New Campaign" onClose={onClose}>
      <FormField label="Campaign Name"><input style={inputStyle} value={form.name} onChange={e => set("name", e.target.value)} placeholder="Spring Running Campaign" /></FormField>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <FormField label="Total Budget ($)"><input style={inputStyle} type="number" value={form.total_budget} onChange={e => set("total_budget", e.target.value)} placeholder="10000" /></FormField>
        <FormField label="Daily Budget ($)"><input style={inputStyle} type="number" value={form.daily_budget} onChange={e => set("daily_budget", e.target.value)} placeholder="Optional" /></FormField>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <FormField label="Start Date"><input style={inputStyle} type="date" value={form.start_date} onChange={e => set("start_date", e.target.value)} /></FormField>
        <FormField label="End Date"><input style={inputStyle} type="date" value={form.end_date} onChange={e => set("end_date", e.target.value)} /></FormField>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
        <button style={btnPrimary} onClick={submit}>Create Campaign</button>
      </div>
    </Modal>
  );
}

// ── Advertiser Detail Page ──────────────────────────────────────
export function AdvertiserDetailPage({ advertiserId, navigate }) {
  const [tab, setTab] = useState("overview");
  const [showEdit, setShowEdit] = useState(false);
  const [showNewCampaign, setShowNewCampaign] = useState(false);
  const [toast, setToast] = useState(null);
  const [days, setDays] = useState(30);

  const { data: adv, loading: loadAdv, reload: reloadAdv } = useFetch(
    () => api.get(`/portal/advertisers/${advertiserId}`).catch(() => MOCK.advertisers.find(a => a.advertiser_id === advertiserId) || MOCK.advertisers[0]),
    [advertiserId]
  );

  const { data: analytics, loading: loadAn } = useFetch(
    () => api.get(`/portal/advertisers/${advertiserId}/analytics?days=${days}`).catch(() => MOCK.advertiserAnalytics),
    [advertiserId, days]
  );

  const { data: campaigns, loading: loadCamp, reload: reloadCamp } = useFetch(
    () => api.get(`/portal/advertisers/${advertiserId}/campaigns?limit=100`).catch(() => MOCK.campaigns),
    [advertiserId]
  );

  if (loadAdv || loadAn) return <Spinner />;

  const an = analytics || MOCK.advertiserAnalytics;

  return (
    <div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#64748b", marginBottom: 20 }}>
        <button onClick={() => navigate("advertisers")} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", padding: 0, fontSize: 13 }}>Advertisers</button>
        <ChevronRight size={14} />
        <span style={{ color: "#e2e8f0" }}>{adv?.name || advertiserId}</span>
      </div>

      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24,
        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 12, padding: "22px 26px",
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>{adv?.name}</h1>
            <StatusBadge status={adv?.status || "active"} />
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>
            {adv?.company_name} &middot; {adv?.contact_email}
          </div>
        </div>
        <button style={btnSecondary} onClick={() => setShowEdit(true)}>
          <Pencil size={13} style={{ marginRight: 6 }} /> Edit
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid rgba(255,255,255,0.07)", marginBottom: 24 }}>
        {["overview", "campaigns"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "12px 20px", fontSize: 13, fontWeight: 500, border: "none", cursor: "pointer",
            background: "transparent", color: tab === t ? "#f59e0b" : "#94a3b8",
            borderBottom: tab === t ? "2px solid #f59e0b" : "2px solid transparent",
            transition: "all 0.2s", textTransform: "capitalize",
          }}>{t}</button>
        ))}
      </div>

      {tab === "overview" && (
        <div>
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 24 }}>
            <KPICard icon={Target} label="Total Campaigns" value={an.total_campaigns} />
            <KPICard icon={Play} label="Active Campaigns" value={an.active_campaigns} accent />
            <KPICard icon={Eye} label="Impressions" value={fmt.num(an.impressions)} />
            <KPICard icon={MousePointerClick} label="Clicks" value={fmt.num(an.clicks)} />
            <KPICard icon={TrendingUp} label="CTR" value={fmt.pct(an.ctr)} />
          </div>
          <div style={{
            background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: 12, padding: "22px 26px",
          }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: "0 0 16px" }}>Budget Utilization</h3>
            <BudgetBar spent={an.total_spent} total={an.total_budget} />
          </div>
        </div>
      )}

      {tab === "campaigns" && (
        <div>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
            <button style={btnPrimary} onClick={() => setShowNewCampaign(true)}>
              <Plus size={14} /> New Campaign
            </button>
          </div>
          {loadCamp ? <Spinner /> : (campaigns || []).length === 0 ? (
            <EmptyState icon={Target} title="No campaigns" desc="Create your first campaign to start running ads." action="New Campaign" onAction={() => setShowNewCampaign(true)} />
          ) : (
            <div style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: 12, overflow: "hidden",
            }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    {["Name", "Status", "Budget", "Spent", "Daily Cap", "Start", "End"].map(h => (
                      <th key={h} style={{
                        padding: "12px 16px", textAlign: "left", fontSize: 11, fontWeight: 600,
                        color: "#64748b", letterSpacing: "0.05em", textTransform: "uppercase",
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(campaigns || []).map((c, i) => (
                    <tr key={c.campaign_id}
                      onClick={() => navigate("campaign", { campaignId: c.campaign_id, advertiserId })}
                      style={{
                        borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer",
                        background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
                      onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)"}
                    >
                      <td style={{ padding: "14px 16px", color: "#e2e8f0", fontWeight: 500 }}>{c.name}</td>
                      <td style={{ padding: "14px 16px" }}><StatusBadge status={c.status} /></td>
                      <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{fmt.money(c.total_budget)}</td>
                      <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{fmt.money(c.total_spent)}</td>
                      <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{c.daily_budget ? fmt.money(c.daily_budget) : "—"}</td>
                      <td style={{ padding: "14px 16px", color: "#64748b" }}>{fmt.date(c.start_date)}</td>
                      <td style={{ padding: "14px 16px", color: "#64748b" }}>{fmt.date(c.end_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showNewCampaign && (
        <CreateCampaignModal
          advertiserId={advertiserId}
          onClose={() => setShowNewCampaign(false)}
          onSuccess={() => { setShowNewCampaign(false); reloadCamp(); setToast({ message: "Campaign created", type: "success" }); }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}
      {showEdit && (
        <EditAdvertiserModal
          adv={adv}
          onClose={() => setShowEdit(false)}
          onSuccess={() => { setShowEdit(false); reloadAdv(); setToast({ message: "Advertiser updated", type: "success" }); }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}
    </div>
  );
}