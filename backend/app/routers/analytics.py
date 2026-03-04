"""
GET /analytics/summary  —  quick dashboard numbers.

Returns impressions, clicks, engagements, CTR, estimated revenue,
and the top-performing ads over a given window.  Simple enough to
power an internal dashboard; we'll make it fancier later.
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
