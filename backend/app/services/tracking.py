"""
Tracking URL generation + event logging (impressions, clicks, engagements).

The tracking URL wraps the advertiser's CTA so every click routes through
our /track/click endpoint first, letting us log it before redirecting.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import structlog

from app.core.config import get_settings
from app.core.db import get_pg
from app.models.schemas import EngagementMetrics

log = structlog.get_logger()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Tracking URL generation ─────────────────────────────────────────────

def generate_tracking_url(ad_id: str, session_id: str, cta_url: str) -> str:
    """
    Wraps the raw advertiser CTA into a redirect URL through our server.
    The LLM receives these URLs (not the raw ones) so every click
    passes through /track/click for logging.
    """
    settings = get_settings()
    params = urlencode({
        "ad_id": ad_id,
        "session_id": session_id,
        "redirect": cta_url,
    })
    return f"{settings.base_url}/track/click?{params}"


def generate_tracking_urls(ads: list, session_id: str) -> dict[str, str]:
    """Convenience: generate tracking URLs for a list of Ad objects."""
    return {
        ad.ad_id: generate_tracking_url(ad.ad_id, session_id, ad.cta_url)
        for ad in ads
    }


# ── Event logging ────────────────────────────────────────────────────────

async def log_impression(session_id: str, ad_id: str, turn_number: int):
    """
    Called right after we confirm the response included an ad.
    Also deducts from the ad's budget using CPM pricing.
    """
    pool = get_pg()

    await pool.execute(
        """
        INSERT INTO events (event_type, session_id, ad_id, payload)
        VALUES ($1, $2, $3::uuid, $4)
        """,
        "impression",
        session_id,
        ad_id,
        json.dumps({"turn_number": turn_number, "timestamp": _now_iso()}),
    )

    # deduct cost from budget (CPM = cost per 1000 impressions)
    await pool.execute(
        """
        UPDATE ads
        SET budget_remaining = budget_remaining - (bid_cpm / 1000)
        WHERE ad_id = $1::uuid
        """,
        ad_id,
    )

    # ── campaign-level budget tracking ───────────────────────────────
    campaign_row = await pool.fetchrow(
        "SELECT campaign_id, bid_cpm FROM ads WHERE ad_id = $1::uuid",
        ad_id,
    )
    if campaign_row and campaign_row["campaign_id"]:
        from app.services.budget import record_spend
        cost = float(campaign_row["bid_cpm"]) / 1000.0
        await record_spend(str(campaign_row["campaign_id"]), cost)

    log.info("event.impression", session_id=session_id, ad_id=ad_id)

    log.info("event.impression", session_id=session_id, ad_id=ad_id)


async def log_click(session_id: str, ad_id: str, cta_url: str):
    """Called from the /track/click redirect endpoint."""
    pool = get_pg()
    await pool.execute(
        """
        INSERT INTO events (event_type, session_id, ad_id, payload)
        VALUES ($1, $2, $3::uuid, $4)
        """,
        "click",
        session_id,
        ad_id,
        json.dumps({"cta_url": cta_url, "timestamp": _now_iso()}),
    )
    log.info("event.click", session_id=session_id, ad_id=ad_id)


async def log_engagement(
    session_id: str,
    ad_id: str,
    follow_up_message: str,
    metrics: "EngagementMetrics | None" = None,
):
    """Called when the engagement classifier detects engagement with a product."""
    pool = get_pg()

    payload = {
        "follow_up_message": follow_up_message,
        "timestamp": _now_iso(),
    }
    if metrics:
        payload.update({
            "engagement_type": metrics.engagement_type.value,
            "engagement_score": metrics.engagement_score,
            "sentiment_toward_ad": metrics.sentiment_toward_ad,
            "ad_naturalness_score": metrics.ad_naturalness_score,
            "purchase_proximity": metrics.purchase_proximity,
            "follow_up_topic_match": metrics.follow_up_topic_match,
            "reasoning": metrics.reasoning,
        })

    await pool.execute(
        """
        INSERT INTO events (event_type, session_id, ad_id, payload)
        VALUES ($1, $2, $3::uuid, $4)
        """,
        "engagement",
        session_id,
        ad_id,
        json.dumps(payload),
    )
    log.info("event.engagement", session_id=session_id, ad_id=ad_id)
