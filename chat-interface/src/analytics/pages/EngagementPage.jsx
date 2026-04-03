import { useState } from "react";
import {
  AreaChart, Area, ComposedChart, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { MessageSquare, Activity, Sparkles, Zap } from "lucide-react";
import { api } from "../api/client";
import { MOCK } from "../mocks/data";
import { useFetch } from "../hooks/useFetch";
import { fmt, scoreColor } from "../utils/helpers";
import { KPICard, TimeRangeSelector, EmptyState, Spinner, LegendItem } from "../components/ui";

const chartTooltipStyle = {
    contentStyle: {
      background: "#1a1a22", border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: 10, padding: "10px 14px", fontSize: 12, color: "#e2e8f0",
    },
    labelStyle: { color: "#94a3b8", fontWeight: 600, marginBottom: 4 },
  };


const ENGAGEMENT_TYPE_LABELS = {
  product_inquiries: "Product Inquiry",
  comparisons: "Comparison",
  price_inquiries: "Price Inquiry",
  purchase_intents: "Purchase Intent",
  negative_reactions: "Negative Reaction",
  dismissals: "Dismissal",
};

const TYPE_KEYS = Object.keys(ENGAGEMENT_TYPE_LABELS);
const PIE_COLORS = ["#f59e0b", "#60a5fa", "#34d399", "#a78bfa", "#f87171", "#94a3b8"];

export function EngagementPage() {
  const [days, setDays] = useState(7);

  const { data: byAd, loading: loadAd } = useFetch(
    () => api.get(`/analytics/engagement?days=${days}`).catch(() => MOCK.engagementByAd),
    [days],
  );

  const { data: timeseries, loading: loadTs } = useFetch(
    () => api.get(`/analytics/engagement/timeseries?days=${days}`).catch(() => MOCK.engagementTimeseries(days)),
    [days],
  );

  if (loadAd || loadTs) return <Spinner />;

  const ads = byAd || [];
  const ts = timeseries || [];

  /* ── Aggregate KPIs across all ads ─────────────────────────── */
  const totals = ads.reduce(
    (acc, a) => ({
      engagements: acc.engagements + (a.total_engagements || 0),
      scoreSum: acc.scoreSum + (a.avg_engagement_score || 0) * (a.total_engagements || 0),
      natSum: acc.natSum + (a.avg_naturalness_score || 0) * (a.total_engagements || 0),
      purchSum: acc.purchSum + (a.avg_purchase_proximity || 0) * (a.total_engagements || 0),
      positive: acc.positive + (a.positive_sentiment || 0),
      negative: acc.negative + (a.negative_sentiment || 0),
    }),
    { engagements: 0, scoreSum: 0, natSum: 0, purchSum: 0, positive: 0, negative: 0 },
  );

  const avgScore = totals.engagements > 0 ? totals.scoreSum / totals.engagements : 0;
  const avgNat   = totals.engagements > 0 ? totals.natSum / totals.engagements : 0;
  const avgPurch = totals.engagements > 0 ? totals.purchSum / totals.engagements : 0;

  /* ── Pie data: engagement type breakdown ───────────────────── */
  const pieData = TYPE_KEYS
    .map(k => ({ name: ENGAGEMENT_TYPE_LABELS[k], value: ads.reduce((s, a) => s + (a[k] || 0), 0) }))
    .filter(d => d.value > 0);

  /* ── Donut data: sentiment ─────────────────────────────────── */
  const sentimentData = [
    { name: "Positive", value: totals.positive, color: "#34d399" },
    { name: "Negative", value: totals.negative, color: "#f87171" },
    { name: "Neutral",  value: Math.max(0, totals.engagements - totals.positive - totals.negative), color: "#64748b" },
  ].filter(d => d.value > 0);

  /* ── Render ────────────────────────────────────────────────── */
  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0, letterSpacing: "-0.02em" }}>Engagement Analytics</h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>Detailed engagement metrics across all ads</p>
        </div>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {/* KPI Cards */}
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 28 }}>
        <KPICard icon={MessageSquare} label="Total Engagements" value={fmt.num(totals.engagements)} accent />
        <KPICard icon={Activity}      label="Avg Engagement Score" value={avgScore.toFixed(2)}
          sub={<span style={{ color: scoreColor(avgScore) }}>out of 1.0</span>} />
        <KPICard icon={Sparkles}      label="Avg Naturalness" value={avgNat.toFixed(2)}
          sub={<span style={{ color: scoreColor(avgNat) }}>out of 1.0</span>} />
        <KPICard icon={Zap}           label="Avg Purchase Proximity" value={avgPurch.toFixed(2)}
          sub={<span style={{ color: scoreColor(avgPurch) }}>out of 1.0</span>} />
      </div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 28 }}>

        {/* Engagement Type Breakdown */}
        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, padding: "22px 26px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: "0 0 16px" }}>Engagement Type Breakdown</h3>
          {pieData.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: "#64748b", fontSize: 13 }}>No engagement data yet</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} innerRadius={40} dataKey="value" paddingAngle={2}>
                    {pieData.map((_, idx) => <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip {...chartTooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center", marginTop: 8 }}>
                {pieData.map((d, i) => (
                  <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#94a3b8" }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    {d.name} ({d.value})
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Sentiment Distribution */}
        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, padding: "22px 26px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: "0 0 16px" }}>Sentiment Toward Ads</h3>
          {sentimentData.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: "#64748b", fontSize: 13 }}>No sentiment data yet</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={sentimentData} cx="50%" cy="50%" outerRadius={80} innerRadius={40} dataKey="value" paddingAngle={2}>
                    {sentimentData.map((d, idx) => <Cell key={idx} fill={d.color} />)}
                  </Pie>
                  <Tooltip {...chartTooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: "flex", gap: 20, justifyContent: "center", marginTop: 8 }}>
                {sentimentData.map(d => (
                  <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#94a3b8" }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: d.color }} />
                    {d.name} ({d.value})
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Engagement Trend Chart */}
      {ts.length > 0 && (
        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, padding: "22px 26px", marginBottom: 28 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: "0 0 20px" }}>Engagement Trends</h3>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={ts}>
              <defs>
                <linearGradient id="engGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tickFormatter={fmt.shortDate} stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis yAxisId="left"  stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} domain={[0, 1]} />
              <Tooltip {...chartTooltipStyle} labelFormatter={fmt.shortDate} />
              <Area yAxisId="left"  type="monotone" dataKey="engagements"    fill="url(#engGrad)" stroke="#f59e0b" strokeWidth={2} name="Engagements" />
              <Line yAxisId="right" type="monotone" dataKey="avg_score"      stroke="#a78bfa" strokeWidth={2} dot={false} name="Avg Score" />
              <Line yAxisId="right" type="monotone" dataKey="avg_naturalness" stroke="#34d399" strokeWidth={2} dot={false} name="Avg Naturalness" />
            </ComposedChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 24, justifyContent: "center", marginTop: 12 }}>
            <LegendItem color="#f59e0b" label="Engagements" />
            <LegendItem color="#a78bfa" label="Avg Score" />
            <LegendItem color="#34d399" label="Avg Naturalness" />
          </div>
        </div>
      )}

      {/* Per-Ad Engagement Table */}
      <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
        <div style={{ padding: "18px 22px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: 0 }}>Per-Ad Engagement</h3>
        </div>
        {ads.length === 0 ? (
          <EmptyState icon={MessageSquare} title="No engagement data" desc="Engagement metrics will appear here once users interact with ads." />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  {["Product", "Engagements", "Avg Score", "Naturalness", "Purchase Prox.", "Sentiment", "Top Type"].map(h => (
                    <th key={h} style={{
                      padding: "12px 16px", textAlign: "left", fontSize: 11, fontWeight: 600,
                      color: "#64748b", letterSpacing: "0.05em", textTransform: "uppercase",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ads.map((ad, i) => {
                  const typeEntries = TYPE_KEYS.map(k => ({ key: k, val: ad[k] || 0 })).sort((a, b) => b.val - a.val);
                  const topType = typeEntries[0]?.val > 0 ? ENGAGEMENT_TYPE_LABELS[typeEntries[0].key] : "—";
                  const posPct = ad.total_engagements > 0 ? (ad.positive_sentiment || 0) / ad.total_engagements : 0;

                  return (
                    <tr key={ad.ad_id} style={{
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                      background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                    }}>
                      <td style={{ padding: "14px 16px", color: "#e2e8f0", fontWeight: 500 }}>{ad.product_name}</td>
                      <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{fmt.num(ad.total_engagements)}</td>
                      <td style={{ padding: "14px 16px" }}>
                        <span style={{ color: scoreColor(ad.avg_engagement_score), fontWeight: 600 }}>
                          {(ad.avg_engagement_score || 0).toFixed(2)}
                        </span>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <span style={{ color: scoreColor(ad.avg_naturalness_score), fontWeight: 600 }}>
                          {(ad.avg_naturalness_score || 0).toFixed(2)}
                        </span>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <span style={{ color: scoreColor(ad.avg_purchase_proximity), fontWeight: 600 }}>
                          {(ad.avg_purchase_proximity || 0).toFixed(2)}
                        </span>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <div style={{ width: 48, height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
                            <div style={{ width: `${posPct * 100}%`, height: "100%", background: "#34d399", borderRadius: 3 }} />
                          </div>
                          <span style={{ fontSize: 11, color: "#94a3b8" }}>{(posPct * 100).toFixed(0)}%+</span>
                        </div>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 4,
                          background: "rgba(167,139,250,0.1)", color: "#a78bfa", fontSize: 11, fontWeight: 500,
                        }}>{topType}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}