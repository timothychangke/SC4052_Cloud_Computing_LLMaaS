import { useState } from "react";
import {
  Area, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ComposedChart
} from "recharts";
import {
  ChevronRight, Plus, Pencil, Pause, Play, Trash2, Tag,
  Eye, MousePointerClick, MessageSquare, TrendingUp, DollarSign, Link
} from "lucide-react";
import { api } from "../api/client";
import { MOCK } from "../mocks/data";
import { useFetch } from "../hooks/useFetch";
import { fmt, inputStyle, btnPrimary, btnSecondary, chartTooltipStyle } from "../utils/helpers";
import {
  StatusBadge, KPICard, BudgetBar, TimeRangeSelector,
  EmptyState, Toast, Spinner, Modal, FormField, TagInput, LegendItem
} from "../components/ui";

// ── Edit Campaign Modal ─────────────────────────────────────────
function EditCampaignModal({ camp, onClose, onSuccess, onError }) {
  const [form, setForm] = useState({
    name: camp.name || "", total_budget: camp.total_budget || "",
    daily_budget: camp.daily_budget || "", start_date: camp.start_date || "", end_date: camp.end_date || "",
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = async () => {
    try {
      const body = {};
      if (form.name !== camp.name) body.name = form.name;
      body.total_budget = parseFloat(form.total_budget) || camp.total_budget;
      body.daily_budget = form.daily_budget ? parseFloat(form.daily_budget) : 0;
      if (form.start_date) body.start_date = form.start_date;
      if (form.end_date) body.end_date = form.end_date;
      await api.patch(`/portal/campaigns/${camp.campaign_id}`, body);
      onSuccess();
    } catch (e) { onError(e.message); }
  };
  return (
    <Modal title="Edit Campaign" onClose={onClose}>
      <FormField label="Name"><input style={inputStyle} value={form.name} onChange={e => set("name", e.target.value)} /></FormField>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <FormField label="Total Budget ($)"><input style={inputStyle} type="number" value={form.total_budget} onChange={e => set("total_budget", e.target.value)} /></FormField>
        <FormField label="Daily Budget ($)"><input style={inputStyle} type="number" value={form.daily_budget} onChange={e => set("daily_budget", e.target.value)} placeholder="0 = no cap" /></FormField>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <FormField label="Start Date"><input style={inputStyle} type="date" value={form.start_date} onChange={e => set("start_date", e.target.value)} /></FormField>
        <FormField label="End Date"><input style={inputStyle} type="date" value={form.end_date} onChange={e => set("end_date", e.target.value)} /></FormField>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
        <button style={btnPrimary} onClick={submit}>Save Changes</button>
      </div>
    </Modal>
  );
}

// ── Create Ad Modal ─────────────────────────────────────────────
function CreateAdModal({ campaignId, onClose, onSuccess, onError }) {
  const [form, setForm] = useState({
    product_name: "", product_description: "", creative_text: "", cta_url: "",
    bid_cpm: "", budget_remaining: "",
    target_topics: [], target_intents: [], brand_safety_tags: [],
  });
  const [urlInput, setUrlInput] = useState("");
  const [extracting, setExtracting] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const extractFromUrl = async () => {
    if (!urlInput.trim()) return;
    setExtracting(true);
    try {
      const data = await api.post("/portal/ads/extract-from-url", { url: urlInput.trim() });
      setForm(f => ({
        ...f,
        product_name: data.product_name || f.product_name,
        product_description: data.product_description || f.product_description,
        creative_text: data.creative_text || f.creative_text,
        cta_url: data.cta_url || f.cta_url,
        target_topics: data.target_topics?.length ? data.target_topics : f.target_topics,
        target_intents: data.target_intents?.length ? data.target_intents : f.target_intents,
        brand_safety_tags: data.brand_safety_tags?.length ? data.brand_safety_tags : f.brand_safety_tags,
      }));
    } catch (e) { onError(`Extraction failed: ${e.message}`); }
    finally { setExtracting(false); }
  };

  const submit = async () => {
    try {
      const body = [{
        product_name: form.product_name, product_description: form.product_description,
        creative_text: form.creative_text, cta_url: form.cta_url,
        bid_cpm: parseFloat(form.bid_cpm) || 0, budget_remaining: parseFloat(form.budget_remaining) || 0,
        target_topics: form.target_topics, target_intents: form.target_intents,
        brand_safety_tags: form.brand_safety_tags,
      }];
      await api.post(`/portal/campaigns/${campaignId}/ads`, body);
      onSuccess();
    } catch (e) { onError(e.message); }
  };

  return (
    <Modal title="New Ad" onClose={onClose} width={600}>
      {/* URL extraction */}
      <div style={{
        background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)",
        borderRadius: 8, padding: "12px 14px", marginBottom: 20,
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "#f59e0b", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
          <Link size={12} /> Fill from product URL
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            style={{ ...inputStyle, flex: 1, fontSize: 13 }}
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && extractFromUrl()}
            placeholder="https://store.example.com/product/..."
            disabled={extracting}
          />
          <button
            style={{ ...btnPrimary, whiteSpace: "nowrap", opacity: extracting ? 0.6 : 1 }}
            onClick={extractFromUrl}
            disabled={extracting || !urlInput.trim()}
          >
            {extracting ? "Extracting…" : "Extract"}
          </button>
        </div>
      </div>

      <FormField label="Product Name"><input style={inputStyle} value={form.product_name} onChange={e => set("product_name", e.target.value)} placeholder="Nike Pegasus 41" /></FormField>
      <FormField label="Product Description"><textarea style={{ ...inputStyle, minHeight: 60, resize: "vertical" }} value={form.product_description} onChange={e => set("product_description", e.target.value)} placeholder="Brief product description..." /></FormField>
      <FormField label="Creative Text"><textarea style={{ ...inputStyle, minHeight: 60, resize: "vertical" }} value={form.creative_text} onChange={e => set("creative_text", e.target.value)} placeholder="The ad copy the LLM will work with..." /></FormField>
      <FormField label="CTA URL"><input style={inputStyle} value={form.cta_url} onChange={e => set("cta_url", e.target.value)} placeholder="https://..." /></FormField>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <FormField label="Bid CPM ($)"><input style={inputStyle} type="number" value={form.bid_cpm} onChange={e => set("bid_cpm", e.target.value)} placeholder="12.50" /></FormField>
        <FormField label="Budget ($)"><input style={inputStyle} type="number" value={form.budget_remaining} onChange={e => set("budget_remaining", e.target.value)} placeholder="5000" /></FormField>
      </div>
      <FormField label="Target Topics"><TagInput value={form.target_topics} onChange={v => set("target_topics", v)} placeholder="e.g. running shoes, marathon" /></FormField>
      <FormField label="Target Intents"><TagInput value={form.target_intents} onChange={v => set("target_intents", v)} placeholder="e.g. product_research, comparison" /></FormField>
      <FormField label="Brand Safety Tags"><TagInput value={form.brand_safety_tags} onChange={v => set("brand_safety_tags", v)} placeholder="e.g. sports, fitness" /></FormField>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
        <button style={btnPrimary} onClick={submit}>Create Ad</button>
      </div>
    </Modal>
  );
}

// ── Campaign Detail Page ────────────────────────────────────────
export function CampaignDetailPage({ campaignId, advertiserId, navigate }) {
  const [days, setDays] = useState(30);
  const [showEdit, setShowEdit] = useState(false);
  const [showNewAd, setShowNewAd] = useState(false);
  const [expandedAd, setExpandedAd] = useState(null);
  const [toast, setToast] = useState(null);

  const { data: campaign, loading: loadCamp, reload: reloadCamp } = useFetch(
    () => api.get(`/portal/campaigns/${campaignId}`).catch(() => MOCK.campaigns[0]),
    [campaignId]
  );

  const { data: analytics, loading: loadAn } = useFetch(
    () => api.get(`/portal/campaigns/${campaignId}/analytics?days=${days}`).catch(() => MOCK.campaignAnalytics(days)),
    [campaignId, days]
  );

  const { data: ads, loading: loadAds, reload: reloadAds } = useFetch(
    () => api.get(`/portal/campaigns/${campaignId}/ads?limit=100`).catch(() => MOCK.ads),
    [campaignId]
  );

  const handlePause = async () => {
    try { await api.post(`/portal/campaigns/${campaignId}/pause`); reloadCamp(); setToast({ message: "Campaign paused", type: "success" }); } catch (e) { setToast({ message: e.message, type: "error" }); }
  };
  const handleResume = async () => {
    try { await api.post(`/portal/campaigns/${campaignId}/resume`); reloadCamp(); setToast({ message: "Campaign resumed", type: "success" }); } catch (e) { setToast({ message: e.message, type: "error" }); }
  };
  const handleDeleteAd = async (adId) => {
    try { await api.del(`/portal/ads/${adId}`); reloadAds(); setToast({ message: "Ad deactivated", type: "success" }); } catch (e) { setToast({ message: e.message, type: "error" }); }
  };

  if (loadCamp || loadAn) return <Spinner />;

  const camp = campaign || MOCK.campaigns[0];
  const an = analytics || MOCK.campaignAnalytics(days);

  return (
    <div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#64748b", marginBottom: 20, flexWrap: "wrap" }}>
        <button onClick={() => navigate("advertisers")} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", padding: 0, fontSize: 13 }}>Advertisers</button>
        <ChevronRight size={14} />
        <button onClick={() => navigate("advertiser", { advertiserId: advertiserId || camp.advertiser_id })} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", padding: 0, fontSize: 13 }}>
          {advertiserId || camp.advertiser_id}
        </button>
        <ChevronRight size={14} />
        <span style={{ color: "#e2e8f0" }}>{camp.name}</span>
      </div>

      {/* Header */}
      <div style={{
        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 12, padding: "22px 26px", marginBottom: 24,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>{camp.name}</h1>
              <StatusBadge status={camp.status} />
            </div>
            <div style={{ fontSize: 13, color: "#64748b" }}>
              {camp.start_date && camp.end_date ? `${fmt.date(camp.start_date)} — ${fmt.date(camp.end_date)}` : "No dates set"}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {camp.status === "active" && (
              <button style={btnSecondary} onClick={handlePause}><Pause size={13} style={{ marginRight: 4 }} /> Pause</button>
            )}
            {(camp.status === "draft" || camp.status === "paused") && (
              <button style={btnPrimary} onClick={handleResume}><Play size={13} style={{ marginRight: 4 }} /> Resume</button>
            )}
            <button style={btnSecondary} onClick={() => setShowEdit(true)}><Pencil size={13} style={{ marginRight: 4 }} /> Edit</button>
          </div>
        </div>
        <BudgetBar spent={camp.total_spent} total={camp.total_budget} />
        {camp.daily_budget > 0 && (
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 10 }}>
            Today: {fmt.money(camp.today_spent)} / {fmt.money(camp.daily_budget)} daily cap
          </div>
        )}
      </div>

      {/* Analytics */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0", margin: 0 }}>Performance</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 24 }}>
        <KPICard icon={Eye} label="Impressions" value={fmt.num(an.impressions)} accent />
        <KPICard icon={MousePointerClick} label="Clicks" value={fmt.num(an.clicks)} />
        <KPICard icon={MessageSquare} label="Engagements" value={fmt.num(an.engagements)} />
        <KPICard icon={TrendingUp} label="CTR" value={fmt.pct(an.ctr)} />
        <KPICard icon={DollarSign} label="Total Spent" value={fmt.money(an.total_spent)} />
      </div>

      {/* Chart */}
      {an.daily_breakdown && an.daily_breakdown.length > 0 && (
        <div style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 12, padding: "22px 26px", marginBottom: 28,
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: "0 0 20px" }}>Daily Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={an.daily_breakdown}>
              <defs>
                <linearGradient id="impGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tickFormatter={fmt.shortDate} stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis yAxisId="left" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
              <Tooltip {...chartTooltipStyle} formatter={(val, name) => [name === "spend" ? fmt.money(val) : fmt.num(val), name.charAt(0).toUpperCase() + name.slice(1)]} labelFormatter={fmt.shortDate} />
              <Area yAxisId="left" type="monotone" dataKey="impressions" fill="url(#impGrad)" stroke="#f59e0b" strokeWidth={2} />
              <Bar yAxisId="left" dataKey="clicks" fill="rgba(96,165,250,0.6)" radius={[3, 3, 0, 0]} barSize={8} />
              <Line yAxisId="right" type="monotone" dataKey="spend" stroke="#34d399" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 24, justifyContent: "center", marginTop: 12 }}>
            <LegendItem color="#f59e0b" label="Impressions" />
            <LegendItem color="#60a5fa" label="Clicks" />
            <LegendItem color="#34d399" label="Spend" />
          </div>
        </div>
      )}

      {/* Ads */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0", margin: 0 }}>Ads</h2>
        <button style={btnPrimary} onClick={() => setShowNewAd(true)}>
          <Plus size={14} /> New Ad
        </button>
      </div>

      {loadAds ? <Spinner /> : (ads || []).length === 0 ? (
        <EmptyState icon={Tag} title="No ads in this campaign" desc="Create ads to start showing product recommendations." action="New Ad" onAction={() => setShowNewAd(true)} />
      ) : (
        <div style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 12, overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {["Product Name", "Bid CPM", "Budget Left", "Status", "Created", ""].map(h => (
                  <th key={h} style={{
                    padding: "12px 16px", textAlign: "left", fontSize: 11, fontWeight: 600,
                    color: "#64748b", letterSpacing: "0.05em", textTransform: "uppercase",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(ads || []).map((ad, i) => (
                <>
                  <tr key={ad.ad_id} style={{
                    borderBottom: expandedAd === ad.ad_id ? "none" : "1px solid rgba(255,255,255,0.04)",
                    cursor: "pointer",
                    background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                    transition: "background 0.15s",
                  }}
                    onClick={() => setExpandedAd(expandedAd === ad.ad_id ? null : ad.ad_id)}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)"}
                  >
                    <td style={{ padding: "14px 16px", color: "#e2e8f0", fontWeight: 500 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <ChevronRight size={14} color="#64748b" style={{ transform: expandedAd === ad.ad_id ? "rotate(90deg)" : "none", transition: "transform 0.2s" }} />
                        {ad.product_name}
                      </div>
                    </td>
                    <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{fmt.money(ad.bid_cpm)}</td>
                    <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{fmt.money(ad.budget_remaining)}</td>
                    <td style={{ padding: "14px 16px" }}><StatusBadge status={ad.active ? "active" : "suspended"} /></td>
                    <td style={{ padding: "14px 16px", color: "#64748b" }}>{fmt.date(ad.created_at)}</td>
                    <td style={{ padding: "14px 16px" }}>
                      <button
                        onClick={e => { e.stopPropagation(); handleDeleteAd(ad.ad_id); }}
                        style={{
                          width: 28, height: 28, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
                          background: "transparent", border: "none", cursor: "pointer", color: "#64748b", transition: "all 0.2s",
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = "rgba(248,113,113,0.12)"; e.currentTarget.style.color = "#f87171"; }}
                        onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#64748b"; }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                  {expandedAd === ad.ad_id && (
                    <tr key={`${ad.ad_id}-exp`}>
                      <td colSpan={6} style={{
                        padding: "0 16px 16px 44px", borderBottom: "1px solid rgba(255,255,255,0.04)",
                        background: "rgba(255,255,255,0.02)",
                      }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px 32px", fontSize: 13, marginTop: 4 }}>
                          <div><span style={{ color: "#64748b" }}>Description:</span> <span style={{ color: "#94a3b8" }}>{ad.product_description}</span></div>
                          <div><span style={{ color: "#64748b" }}>CTA URL:</span> <a href={ad.cta_url} target="_blank" rel="noreferrer" style={{ color: "#f59e0b", textDecoration: "underline" }}>{ad.cta_url}</a></div>
                          <div><span style={{ color: "#64748b" }}>Creative:</span> <span style={{ color: "#94a3b8" }}>{ad.creative_text}</span></div>
                          <div>
                            <span style={{ color: "#64748b" }}>Topics:</span>{" "}
                            {(ad.target_topics || []).map(t => (
                              <span key={t} style={{ display: "inline-block", padding: "2px 8px", borderRadius: 4, background: "rgba(245,158,11,0.1)", color: "#f59e0b", fontSize: 11, marginRight: 4, fontWeight: 500 }}>{t}</span>
                            ))}
                          </div>
                          <div>
                            <span style={{ color: "#64748b" }}>Intents:</span>{" "}
                            {(ad.target_intents || []).map(t => (
                              <span key={t} style={{ display: "inline-block", padding: "2px 8px", borderRadius: 4, background: "rgba(96,165,250,0.1)", color: "#60a5fa", fontSize: 11, marginRight: 4, fontWeight: 500 }}>{t}</span>
                            ))}
                          </div>
                          <div>
                            <span style={{ color: "#64748b" }}>Safety Tags:</span>{" "}
                            {(ad.brand_safety_tags || []).map(t => (
                              <span key={t} style={{ display: "inline-block", padding: "2px 8px", borderRadius: 4, background: "rgba(52,211,153,0.1)", color: "#34d399", fontSize: 11, marginRight: 4, fontWeight: 500 }}>{t}</span>
                            ))}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNewAd && (
        <CreateAdModal
          campaignId={campaignId}
          onClose={() => setShowNewAd(false)}
          onSuccess={() => { setShowNewAd(false); reloadAds(); setToast({ message: "Ad created", type: "success" }); }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}
      {showEdit && (
        <EditCampaignModal
          camp={camp}
          onClose={() => setShowEdit(false)}
          onSuccess={() => { setShowEdit(false); reloadCamp(); setToast({ message: "Campaign updated", type: "success" }); }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}
    </div>
  );
}