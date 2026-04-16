"""
GET /analytics/summary  —  quick dashboard numbers.

Returns impressions, clicks, engagements, CTR, estimated revenue,
and the top-performing ads over a given window.  
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.db import get_pg
from app.models.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(days: int = Query(7, ge=1, le=90)):
    pool = get_pg()

    # counts by event type
    impressions = await pool.fetchval(
        """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'impression'
          AND created_at > NOW() - ($1 || ' days')::interval
        """,
        str(days),
    )

    clicks = await pool.fetchval(
        """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'click'
          AND created_at > NOW() - ($1 || ' days')::interval
        """,
        str(days),
    )

    engagements = await pool.fetchval(
        """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'engagement'
          AND created_at > NOW() - ($1 || ' days')::interval
        """,
        str(days),
    )

    ctr = (clicks / impressions) if impressions > 0 else 0.0

    # average CPM across active ads — used for revenue estimate
    avg_cpm = await pool.fetchval("SELECT COALESCE(AVG(bid_cpm), 0) FROM ads WHERE active = true")
    estimated_revenue = float(impressions) * float(avg_cpm) / 1000.0

    # top 10 ads by impression count in the window
    top_rows = await pool.fetch(
        """
        SELECT
            a.product_name,
            a.ad_id::text AS ad_id,
            COUNT(*) FILTER (WHERE e.event_type = 'impression') AS impressions,
            COUNT(*) FILTER (WHERE e.event_type = 'click') AS clicks,
            COUNT(*) FILTER (WHERE e.event_type = 'engagement') AS engagements
        FROM events e
        JOIN ads a ON e.ad_id = a.ad_id
        WHERE e.created_at > NOW() - ($1 || ' days')::interval
        GROUP BY a.ad_id, a.product_name
        ORDER BY impressions DESC
        LIMIT 10
        """,
        str(days),
    )

    return AnalyticsSummary(
        impressions=impressions,
        clicks=clicks,
        engagements=engagements,
        ctr=round(ctr, 4),
        estimated_revenue=round(estimated_revenue, 2),
        top_ads=[dict(r) for r in top_rows],
    )

@router.get("/engagement")
async def engagement_analytics(
    days: int = Query(7, ge=1, le=90),
    ad_id: str | None = Query(None),
):
    """Aggregated engagement metrics per ad, for the dashboard."""
    pool = get_pg()

    rows = await pool.fetch(
        """
        SELECT
            e.ad_id::text AS ad_id,
            a.product_name,
            COUNT(*) AS total_engagements,
            AVG((e.payload->>'engagement_score')::float) AS avg_engagement_score,
            AVG((e.payload->>'ad_naturalness_score')::float) AS avg_naturalness_score,
            AVG((e.payload->>'purchase_proximity')::float) AS avg_purchase_proximity,
            COUNT(*) FILTER (WHERE e.payload->>'engagement_type' = 'product_inquiry') AS product_inquiries,
            COUNT(*) FILTER (WHERE e.payload->>'engagement_type' = 'comparison') AS comparisons,
            COUNT(*) FILTER (WHERE e.payload->>'engagement_type' = 'price_inquiry') AS price_inquiries,
            COUNT(*) FILTER (WHERE e.payload->>'engagement_type' = 'purchase_intent') AS purchase_intents,
            COUNT(*) FILTER (WHERE e.payload->>'engagement_type' = 'negative_reaction') AS negative_reactions,
            COUNT(*) FILTER (WHERE e.payload->>'engagement_type' = 'dismissal') AS dismissals,
            COUNT(*) FILTER (WHERE e.payload->>'sentiment_toward_ad' = 'positive') AS positive_sentiment,
            COUNT(*) FILTER (WHERE e.payload->>'sentiment_toward_ad' = 'negative') AS negative_sentiment,
            COUNT(*) FILTER (WHERE (e.payload->>'follow_up_topic_match')::bool = true) AS topic_matches
        FROM events e
        JOIN ads a ON e.ad_id = a.ad_id
        WHERE e.event_type = 'engagement'
          AND e.created_at > NOW() - ($1 || ' days')::interval
          AND ($2::text IS NULL OR e.ad_id::text = $2)
        GROUP BY e.ad_id, a.product_name
        ORDER BY total_engagements DESC
        """,
        str(days),
        ad_id,
    )

    return [dict(r) for r in rows]


@router.get("/engagement/timeseries")
async def engagement_timeseries(
    days: int = Query(7, ge=1, le=90),
    ad_id: str | None = Query(None),
):
    """Daily engagement metrics for chart visualization."""
    pool = get_pg()

    rows = await pool.fetch(
        """
        SELECT
            DATE(e.created_at) AS date,
            COUNT(*) AS engagements,
            AVG((e.payload->>'engagement_score')::float) AS avg_score,
            AVG((e.payload->>'ad_naturalness_score')::float) AS avg_naturalness
        FROM events e
        WHERE e.event_type = 'engagement'
          AND e.created_at > NOW() - ($1 || ' days')::interval
          AND ($2::text IS NULL OR e.ad_id::text = $2)
        GROUP BY DATE(e.created_at)
        ORDER BY date
        """,
        str(days),
        ad_id,
    )

    return [
        {
            "date": str(r["date"]),
            "engagements": r["engagements"],
            "avg_score": round(float(r["avg_score"] or 0), 3),
            "avg_naturalness": round(float(r["avg_naturalness"] or 0), 3),
        }
        for r in rows
    ]
