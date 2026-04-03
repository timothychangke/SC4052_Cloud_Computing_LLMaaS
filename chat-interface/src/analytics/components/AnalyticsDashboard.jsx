import { useState } from "react";
import { LayoutDashboard, Users, Activity } from "lucide-react";
import { DashboardPage } from "../pages/DashboardPage";
import { AdvertisersPage } from "../pages/AdvertisersPage";
import { AdvertiserDetailPage } from "../pages/AdvertiserDetailPage";
import { CampaignDetailPage } from "../pages/CampaignDetailPage";
import { EngagementPage } from "../pages/EngagementPage";

const GLOBAL_STYLES = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  button { font-family: inherit; }
  input, textarea, select { font-family: inherit; }
  input:focus, textarea:focus, select:focus {
    border-color: rgba(245,158,11,0.4) !important;
    box-shadow: 0 0 0 3px rgba(245,158,11,0.08);
  }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  select option { background: #1a1a22; color: #e2e8f0; }
  input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(0.7); }
`;

const NAV_ITEMS = [
  { id: "dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { id: "engagement", icon: Activity, label: "Engagement" },
  { id: "advertisers", icon: Users, label: "Advertisers" },
];

export default function AnalyticsDashboard() {
  const [route, setRoute] = useState({ page: "dashboard", params: {} });
  const navigate = (page, params = {}) => setRoute({ page, params });

  const renderPage = () => {
    switch (route.page) {
      case "dashboard": return <DashboardPage />;
      case "advertisers": return <AdvertisersPage navigate={navigate} />;
      case "engagement": return <EngagementPage />;
      case "advertiser": return <AdvertiserDetailPage advertiserId={route.params.advertiserId} navigate={navigate} />;
      case "campaign": return <CampaignDetailPage campaignId={route.params.campaignId} advertiserId={route.params.advertiserId} navigate={navigate} />;
      default: return <DashboardPage />;
    }
  };

  return (
    <div style={{
      display: "flex", height: "100vh", fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      background: "#0d0d10", color: "#e2e8f0", overflow: "hidden",
    }}>
      <style>{GLOBAL_STYLES}</style>

      {/* Sidebar */}
      <div style={{
        width: 220, flexShrink: 0, background: "rgba(13,13,16,0.95)",
        borderRight: "1px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column",
        backdropFilter: "blur(12px)",
      }}>
        {/* Brand */}
        <div style={{ padding: "20px 16px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 10,
              background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.25)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 700, color: "#f59e0b",
            }}>A</div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em" }}>Ad LLM</div>
              <div style={{ fontSize: 10, color: "#64748b", letterSpacing: "0.06em", textTransform: "uppercase" }}>Analytics</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <div style={{ padding: "12px 8px", flex: 1 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", padding: "8px 10px 6px" }}>
            Navigation
          </div>
          {NAV_ITEMS.map(item => {
            const active = route.page === item.id || (item.id === "advertisers" && ["advertiser", "campaign"].includes(route.page));
            return (
              <button key={item.id} onClick={() => navigate(item.id)} style={{
                width: "100%", display: "flex", alignItems: "center", gap: 10,
                padding: "10px 12px", borderRadius: 8, border: "none", cursor: "pointer",
                background: active ? "rgba(245,158,11,0.1)" : "transparent",
                color: active ? "#f59e0b" : "#94a3b8", fontSize: 13, fontWeight: 500,
                transition: "all 0.15s", position: "relative", textAlign: "left",
              }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}
              >
                {active && <div style={{
                  position: "absolute", left: 0, top: 8, bottom: 8, width: 3,
                  borderRadius: "0 2px 2px 0", background: "#f59e0b",
                }} />}
                <item.icon size={16} />
                {item.label}
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{ padding: "12px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px" }}>
            <div style={{
              width: 30, height: 30, borderRadius: "50%", background: "rgba(245,158,11,0.1)",
              border: "1.5px solid rgba(245,158,11,0.3)", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 12, fontWeight: 600, color: "#f59e0b",
            }}>P</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 500, color: "#e2e8f0" }}>Platform Admin</div>
              <div style={{ fontSize: 10, color: "#64748b" }}>Internal Portal</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "28px 36px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          {renderPage()}
        </div>
      </div>
    </div>
  );
}