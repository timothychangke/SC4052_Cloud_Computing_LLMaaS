export const MOCK = {
  summary: (days) => ({
    impressions: Math.round(14320 * days / 7),
    clicks: Math.round(287 * days / 7),
    engagements: Math.round(412 * days / 7),
    ctr: 0.02,
    estimated_revenue: +(178.99 * days / 7).toFixed(2),
    top_ads: [
      { product_name: "Nike Pegasus 41", ad_id: "a1b2c3d4", impressions: 3200, clicks: 64, engagements: 89 },
      { product_name: "Sony WH-1000XM5", ad_id: "b2c3d4e5", impressions: 2800, clicks: 72, engagements: 65 },
      { product_name: "Dyson V15 Detect", ad_id: "c3d4e5f6", impressions: 2100, clicks: 38, engagements: 52 },
      { product_name: "Kindle Paperwhite", ad_id: "d4e5f6g7", impressions: 1950, clicks: 45, engagements: 41 },
      { product_name: "Allbirds Tree Runners", ad_id: "e5f6g7h8", impressions: 1800, clicks: 31, engagements: 38 },
    ],
  }),
  advertisers: [
    { advertiser_id: "adv_nike", name: "Nike Inc.", company_name: "Nike Inc.", contact_email: "ads@nike.com", billing_email: "billing@nike.com", status: "active", created_at: "2025-01-15 10:30:00" },
    { advertiser_id: "adv_sony", name: "Sony Electronics", company_name: "Sony Group Corp.", contact_email: "ads@sony.com", billing_email: "billing@sony.com", status: "active", created_at: "2025-02-01 09:00:00" },
    { advertiser_id: "adv_dyson", name: "Dyson Ltd.", company_name: "Dyson Ltd.", contact_email: "marketing@dyson.com", billing_email: "finance@dyson.com", status: "active", created_at: "2025-02-10 14:20:00" },
    { advertiser_id: "adv_paused", name: "Acme Corp", company_name: "Acme Corporation", contact_email: "ads@acme.com", billing_email: "billing@acme.com", status: "suspended", created_at: "2025-01-20 11:45:00" },
  ],
  advertiserAnalytics: {
    advertiser_id: "adv_nike", name: "Nike Inc.", total_campaigns: 5, active_campaigns: 2,
    total_spent: 4523.75, total_budget: 25000.0, impressions: 36200, clicks: 724, engagements: 1020, ctr: 0.02,
    campaigns: [
      { campaign_id: "camp_1", name: "Spring Running Campaign", status: "active", total_budget: 10000, total_spent: 2345.50 },
      { campaign_id: "camp_2", name: "Summer Lifestyle", status: "active", total_budget: 8000, total_spent: 1200.25 },
      { campaign_id: "camp_3", name: "Winter Sale Push", status: "completed", total_budget: 5000, total_spent: 4999.80 },
      { campaign_id: "camp_4", name: "Q1 Brand Awareness", status: "paused", total_budget: 2000, total_spent: 978.20 },
    ],
  },
  campaigns: [
    { campaign_id: "camp_1", advertiser_id: "adv_nike", name: "Spring Running Campaign", status: "active", total_budget: 10000, daily_budget: 500, total_spent: 2345.50, today_spent: 123.45, start_date: "2025-04-01", end_date: "2025-06-30", created_at: "2025-03-15 10:35:00", updated_at: "2025-03-15 10:35:00" },
    { campaign_id: "camp_2", advertiser_id: "adv_nike", name: "Summer Lifestyle", status: "active", total_budget: 8000, daily_budget: 400, total_spent: 1200.25, today_spent: 89.30, start_date: "2025-05-01", end_date: "2025-08-31", created_at: "2025-03-20 14:00:00", updated_at: "2025-03-20 14:00:00" },
    { campaign_id: "camp_3", advertiser_id: "adv_nike", name: "Winter Sale Push", status: "completed", total_budget: 5000, daily_budget: null, total_spent: 4999.80, today_spent: 0, start_date: "2024-11-01", end_date: "2025-01-31", created_at: "2024-10-15 09:00:00", updated_at: "2025-01-31 23:59:00" },
  ],
  campaignAnalytics: (days) => {
    const daily = [];
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(); d.setDate(d.getDate() - i);
      daily.push({
        date: d.toISOString().split("T")[0],
        impressions: 400 + Math.floor(Math.random() * 300),
        clicks: 8 + Math.floor(Math.random() * 12),
        engagements: 12 + Math.floor(Math.random() * 15),
        spend: +(60 + Math.random() * 40).toFixed(2),
      });
    }
    return {
      campaign_id: "camp_1", campaign_name: "Spring Running Campaign", status: "active",
      total_budget: 10000, total_spent: 2345.50, impressions: 18700, clicks: 374,
      engagements: 510, ctr: 0.02, daily_breakdown: daily,
    };
  },
  ads: [
    { ad_id: "ad_001", advertiser_id: "adv_nike", product_name: "Nike Pegasus 41", product_description: "Lightweight daily trainer for neutral runners with responsive ZoomX foam technology.", target_topics: ["running shoes", "marathon", "jogging"], target_intents: ["product_research", "comparison"], creative_text: "The Nike Pegasus 41 offers responsive ZoomX foam for your daily runs.", cta_url: "https://nike.com/pegasus-41", bid_cpm: 12.50, budget_remaining: 4850, brand_safety_tags: ["sports", "fitness"], active: true, created_at: "2025-03-15T10:40:00", updated_at: "2025-03-15T10:40:00" },
    { ad_id: "ad_002", advertiser_id: "adv_nike", product_name: "Nike Air Max 270", product_description: "Iconic lifestyle sneaker with Max Air unit for all-day comfort.", target_topics: ["sneakers", "lifestyle", "fashion"], target_intents: ["product_research", "purchase"], creative_text: "Step into comfort with the Nike Air Max 270.", cta_url: "https://nike.com/air-max-270", bid_cpm: 10.00, budget_remaining: 3200, brand_safety_tags: ["fashion", "lifestyle"], active: true, created_at: "2025-03-16T11:00:00", updated_at: "2025-03-16T11:00:00" },
    { ad_id: "ad_003", advertiser_id: "adv_nike", product_name: "Nike Dri-FIT ADV", product_description: "Advanced moisture-wicking running shirt.", target_topics: ["running apparel", "sportswear"], target_intents: ["product_research"], creative_text: "Stay cool and dry with Nike Dri-FIT ADV technology.", cta_url: "https://nike.com/dri-fit", bid_cpm: 8.00, budget_remaining: 0, brand_safety_tags: ["sports"], active: false, created_at: "2025-03-17T09:30:00", updated_at: "2025-03-18T15:00:00" },
  ],
};