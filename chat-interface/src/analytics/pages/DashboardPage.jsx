import { useState } from "react";
import { Eye, MousePointerClick, MessageSquare, TrendingUp, DollarSign, BarChart3 } from "lucide-react";
import { api } from "../api/client";
import { MOCK } from "../mocks/data";
import { useFetch } from "../hooks/useFetch";
import { fmt, ctrColor } from "../utils/helpers";
import { KPICard, TimeRangeSelector, EmptyState, Spinner } from "../components/ui";

export function DashboardPage() {
  const [days, setDays] = useState(7);
  const { data, loading, error } = useFetch(
    () => api.get(`/analytics/summary?days=${days}`).catch(() => MOCK.summary(days)),
    [days]
  );

  if (loading) return <Spinner />;
  if (error) return <div style={{ padding: 40, color: "#f87171" }}>{error}</div>;
  if (!data) return null;

  const sortedAds = [...(data.top_ads || [])];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0, letterSpacing: "-0.02em" }}>Platform Dashboard</h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>Overview of ad performance across all advertisers</p>
        </div>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 28 }}>
        <KPICard icon={Eye} label="Impressions" value={fmt.num(data.impressions)} accent />
        <KPICard icon={MousePointerClick} label="Clicks" value={fmt.num(data.clicks)} />
        <KPICard icon={MessageSquare} label="Engagements" value={fmt.num(data.engagements)} />
        <KPICard icon={TrendingUp} label="CTR" value={fmt.pct(data.ctr)} />
        <KPICard icon={DollarSign} label="Revenue" value={fmt.money(data.estimated_revenue)} accent />
      </div>

      <div style={{
        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 12, overflow: "hidden",
      }}>
        <div style={{ padding: "18px 22px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", margin: 0 }}>Top Performing Ads</h3>
        </div>
        {sortedAds.length === 0 ? (
          <EmptyState icon={BarChart3} title="No ad data yet" desc="Ads will appear here once impressions are recorded." />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  {["Product Name", "Impressions", "Clicks", "Engagements", "CTR"].map(h => (
                    <th key={h} style={{
                      padding: "12px 18px", textAlign: "left", fontSize: 11, fontWeight: 600,
                      color: "#64748b", letterSpacing: "0.05em", textTransform: "uppercase",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedAds.map((ad, i) => {
                  const ctr = ad.impressions > 0 ? ad.clicks / ad.impressions : 0;
                  return (
                    <tr key={ad.ad_id} style={{
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                      background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                    }}>
                      <td style={{ padding: "14px 18px", color: "#e2e8f0", fontWeight: 500 }}>{ad.product_name}</td>
                      <td style={{ padding: "14px 18px", color: "#94a3b8" }}>{fmt.num(ad.impressions)}</td>
                      <td style={{ padding: "14px 18px", color: "#94a3b8" }}>{fmt.num(ad.clicks)}</td>
                      <td style={{ padding: "14px 18px", color: "#94a3b8" }}>{fmt.num(ad.engagements)}</td>
                      <td style={{ padding: "14px 18px" }}>
                        <span style={{
                          display: "inline-flex", alignItems: "center", gap: 6,
                          color: ctrColor(ctr), fontWeight: 600,
                        }}>
                          <span style={{ width: 7, height: 7, borderRadius: "50%", background: ctrColor(ctr) }} />
                          {fmt.pct(ctr)}
                        </span>
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