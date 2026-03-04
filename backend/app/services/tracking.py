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


async def log_engagement(session_id: str, ad_id: str, follow_up_message: str):
    """Called when the engagement classifier says the user asked about the product."""
    pool = get_pg()
    await pool.execute(
        """
        INSERT INTO events (event_type, session_id, ad_id, payload)
        VALUES ($1, $2, $3::uuid, $4)
        """,
        "engagement",
        session_id,
        ad_id,
        json.dumps({"follow_up_message": follow_up_message, "timestamp": _now_iso()}),
    )
    log.info("event.engagement", session_id=session_id, ad_id=ad_id)
