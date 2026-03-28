"""
Advertiser Portal API.

Self-serve CRUD for advertisers, campaigns, and campaign-level ads,
plus per-advertiser and per-campaign analytics.

No auth yet — add middleware before going to prod.

Endpoints:

  Advertisers:
    POST   /portal/advertisers                              → register
    GET    /portal/advertisers                              → list
    GET    /portal/advertisers/{advertiser_id}              → detail
    PATCH  /portal/advertisers/{advertiser_id}              → update

  Campaigns:
    POST   /portal/advertisers/{advertiser_id}/campaigns    → create
    GET    /portal/advertisers/{advertiser_id}/campaigns    → list for advertiser
    GET    /portal/campaigns/{campaign_id}                  → detail
    PATCH  /portal/campaigns/{campaign_id}                  → update
    POST   /portal/campaigns/{campaign_id}/pause            → pause
    POST   /portal/campaigns/{campaign_id}/resume           → resume

  Ads (within campaigns):
    POST   /portal/campaigns/{campaign_id}/ads              → create ad(s)
    GET    /portal/campaigns/{campaign_id}/ads              → list ads
    PATCH  /portal/ads/{ad_id}                              → update ad
    DELETE /portal/ads/{ad_id}                              → soft-delete

  Analytics:
    GET    /portal/advertisers/{advertiser_id}/analytics    → advertiser rollup
    GET    /portal/campaigns/{campaign_id}/analytics        → campaign detail + daily
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.db import get_pg
from app.services.ai import embed_ad
from app.models.schemas import (
    AdvertiserCreatePayload,
    AdvertiserUpdatePayload,
    AdvertiserResponse,
    CampaignCreatePayload,
    CampaignUpdatePayload,
    CampaignResponse,
    CampaignAdCreatePayload,
    AdUpdatePayload,
    CampaignAnalyticsResponse,
    AdvertiserAnalyticsResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/portal", tags=["portal"])


# ═══════════════════════════════════════════════════════════════════════════
#  ADVERTISERS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/advertisers", response_model=AdvertiserResponse, status_code=201)
async def create_advertiser(payload: AdvertiserCreatePayload):
    pool = get_pg()

    existing = await pool.fetchrow(
        "SELECT 1 FROM advertisers WHERE advertiser_id = $1",
        payload.advertiser_id,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Advertiser ID already exists")

    row = await pool.fetchrow(
        """
        INSERT INTO advertisers (advertiser_id, name, contact_email, company_name,
                                 billing_email, status)
        VALUES ($1, $2, $3, $4, $5, 'active')
        RETURNING advertiser_id, name, contact_email, company_name,
                  billing_email, status, created_at
        """,
        payload.advertiser_id,
        payload.name,
        payload.contact_email,
        payload.company_name,
        payload.billing_email,
    )
    return _advertiser_row_to_response(row)


@router.get("/advertisers", response_model=list[AdvertiserResponse])
async def list_advertisers(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    pool = get_pg()

    if status:
        rows = await pool.fetch(
            """
            SELECT advertiser_id, name, contact_email, company_name,
                   billing_email, status, created_at
            FROM advertisers
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            status, limit, offset,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT advertiser_id, name, contact_email, company_name,
                   billing_email, status, created_at
            FROM advertisers
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
    return [_advertiser_row_to_response(r) for r in rows]


@router.get("/advertisers/{advertiser_id}", response_model=AdvertiserResponse)
async def get_advertiser(advertiser_id: str):
    pool = get_pg()
    row = await pool.fetchrow(
        """
        SELECT advertiser_id, name, contact_email, company_name,
               billing_email, status, created_at
        FROM advertisers WHERE advertiser_id = $1
        """,
        advertiser_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Advertiser not found")
    return _advertiser_row_to_response(row)


@router.patch("/advertisers/{advertiser_id}", response_model=AdvertiserResponse)
async def update_advertiser(advertiser_id: str, payload: AdvertiserUpdatePayload):
    pool = get_pg()

    updates, params, idx = [], [], 1
    for field_name, column in [
        ("name", "name"),
        ("contact_email", "contact_email"),
        ("company_name", "company_name"),
        ("billing_email", "billing_email"),
        ("status", "status"),
    ]:
        value = getattr(payload, field_name)
        if value is not None:
            # enum → string
            updates.append(f"{column} = ${idx}")
            params.append(value.value if hasattr(value, "value") else value)
            idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    params.append(advertiser_id)
    set_clause = ", ".join(updates)

    result = await pool.execute(
        f"UPDATE advertisers SET {set_clause} WHERE advertiser_id = ${idx}",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Advertiser not found")

    return await get_advertiser(advertiser_id)


def _advertiser_row_to_response(row) -> AdvertiserResponse:
    return AdvertiserResponse(
        advertiser_id=row["advertiser_id"],
        name=row["name"],
        contact_email=row["contact_email"],
        company_name=row["company_name"],
        billing_email=row["billing_email"],
        status=row["status"] or "active",
        created_at=str(row["created_at"]),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CAMPAIGNS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/advertisers/{advertiser_id}/campaigns",
    response_model=CampaignResponse,
    status_code=201,
)
async def create_campaign(advertiser_id: str, payload: CampaignCreatePayload):
    pool = get_pg()

    # verify advertiser exists and is active
    adv = await pool.fetchrow(
        "SELECT status FROM advertisers WHERE advertiser_id = $1",
        advertiser_id,
    )
    if not adv:
        raise HTTPException(status_code=404, detail="Advertiser not found")
    if adv["status"] != "active":
        raise HTTPException(status_code=403, detail="Advertiser account is suspended")

    if payload.end_date and payload.start_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

    row = await pool.fetchrow(
        """
        INSERT INTO campaigns (advertiser_id, name, total_budget, daily_budget,
                               start_date, end_date, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'draft')
        RETURNING campaign_id::text, advertiser_id, name, status,
                  total_budget, daily_budget, total_spent, today_spent,
                  start_date, end_date, created_at, updated_at
        """,
        advertiser_id,
        payload.name,
        payload.total_budget,
        payload.daily_budget,
        payload.start_date,
        payload.end_date,
    )
    log.info("portal.campaign_created", campaign_id=row["campaign_id"],
             advertiser=advertiser_id)
    return _campaign_row_to_response(row)


@router.get(
    "/advertisers/{advertiser_id}/campaigns",
    response_model=list[CampaignResponse],
)
async def list_campaigns(
    advertiser_id: str,
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    pool = get_pg()

    if status:
        rows = await pool.fetch(
            """
            SELECT campaign_id::text, advertiser_id, name, status,
                   total_budget, daily_budget, total_spent, today_spent,
                   start_date, end_date, created_at, updated_at
            FROM campaigns
            WHERE advertiser_id = $1 AND status = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            """,
            advertiser_id, status, limit, offset,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT campaign_id::text, advertiser_id, name, status,
                   total_budget, daily_budget, total_spent, today_spent,
                   start_date, end_date, created_at, updated_at
            FROM campaigns
            WHERE advertiser_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            advertiser_id, limit, offset,
        )
    return [_campaign_row_to_response(r) for r in rows]


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str):
    pool = get_pg()
    row = await pool.fetchrow(
        """
        SELECT campaign_id::text, advertiser_id, name, status,
               total_budget, daily_budget, total_spent, today_spent,
               start_date, end_date, created_at, updated_at
        FROM campaigns WHERE campaign_id = $1::uuid
        """,
        campaign_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_row_to_response(row)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: str, payload: CampaignUpdatePayload):
    pool = get_pg()

    # only allow edits on draft or paused campaigns (not active mid-flight)
    current = await pool.fetchrow(
        "SELECT status FROM campaigns WHERE campaign_id = $1::uuid",
        campaign_id,
    )
    if not current:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if current["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot edit a completed campaign")

    updates, params, idx = [], [], 1
    for field_name, column in [
        ("name", "name"),
        ("total_budget", "total_budget"),
        ("daily_budget", "daily_budget"),
        ("start_date", "start_date"),
        ("end_date", "end_date"),
    ]:
        value = getattr(payload, field_name)
        if value is not None:
            # daily_budget=0 means "remove the cap" → store as NULL
            if field_name == "daily_budget" and value == 0:
                updates.append(f"{column} = NULL")
                continue
            updates.append(f"{column} = ${idx}")
            params.append(value)
            idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    updates.append("updated_at = NOW()")
    params.append(campaign_id)
    set_clause = ", ".join(updates)

    await pool.execute(
        f"UPDATE campaigns SET {set_clause} WHERE campaign_id = ${idx}::uuid",
        *params,
    )
    return await get_campaign(campaign_id)


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(campaign_id: str):
    pool = get_pg()
    result = await pool.execute(
        """
        UPDATE campaigns SET status = 'paused', updated_at = NOW()
        WHERE campaign_id = $1::uuid AND status = 'active'
        """,
        campaign_id,
    )
    if result == "UPDATE 0":
        row = await pool.fetchrow(
            "SELECT status FROM campaigns WHERE campaign_id = $1::uuid",
            campaign_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Campaign not found")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause a campaign with status '{row['status']}'",
        )
    log.info("portal.campaign_paused", campaign_id=campaign_id)
    return await get_campaign(campaign_id)


@router.post("/campaigns/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(campaign_id: str):
    pool = get_pg()
    result = await pool.execute(
        """
        UPDATE campaigns SET status = 'active', updated_at = NOW()
        WHERE campaign_id = $1::uuid AND status IN ('draft', 'paused')
        """,
        campaign_id,
    )
    if result == "UPDATE 0":
        row = await pool.fetchrow(
            "SELECT status FROM campaigns WHERE campaign_id = $1::uuid",
            campaign_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Campaign not found")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume a campaign with status '{row['status']}'",
        )
    log.info("portal.campaign_resumed", campaign_id=campaign_id)
    return await get_campaign(campaign_id)


def _campaign_row_to_response(row) -> CampaignResponse:
    return CampaignResponse(
        campaign_id=row["campaign_id"],
        advertiser_id=row["advertiser_id"],
        name=row["name"],
        status=row["status"],
        total_budget=float(row["total_budget"]),
        daily_budget=float(row["daily_budget"]) if row["daily_budget"] else None,
        total_spent=float(row["total_spent"]),
        today_spent=float(row["today_spent"]),
        start_date=str(row["start_date"]) if row["start_date"] else None,
        end_date=str(row["end_date"]) if row["end_date"] else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  ADS (within campaigns)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/campaigns/{campaign_id}/ads", status_code=201)
async def create_campaign_ads(campaign_id: str, ads: list[CampaignAdCreatePayload]):
    """Create one or more ads linked to a campaign."""
    pool = get_pg()

    # verify campaign exists
    campaign = await pool.fetchrow(
        "SELECT advertiser_id, status FROM campaigns WHERE campaign_id = $1::uuid",
        campaign_id,
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot add ads to a completed campaign")

    advertiser_id = campaign["advertiser_id"]
    created_ids = []

    for ad in ads:
        text_to_embed = (
            f"{ad.product_name} {ad.product_description} "
            f"{' '.join(ad.target_topics)}"
        )
        embedding = await embed_ad(text_to_embed)
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        row = await pool.fetchrow(
            """
            INSERT INTO ads (
                advertiser_id, campaign_id, product_name, product_description,
                target_topics, target_intents, creative_text, cta_url,
                bid_cpm, budget_remaining, brand_safety_tags, embedding
            ) VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::vector)
            RETURNING ad_id::text
            """,
            advertiser_id,
            campaign_id,
            ad.product_name,
            ad.product_description,
            ad.target_topics,
            ad.target_intents,
            ad.creative_text,
            ad.cta_url,
            ad.bid_cpm,
            ad.budget_remaining,
            ad.brand_safety_tags,
            embedding_str,
        )
        created_ids.append(row["ad_id"])
        log.info("portal.ad_created", ad_id=row["ad_id"],
                 campaign_id=campaign_id, product=ad.product_name)

    return {"created": len(created_ids), "ad_ids": created_ids}


@router.get("/campaigns/{campaign_id}/ads")
async def list_campaign_ads(
    campaign_id: str,
    active_only: bool = Query(True),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    pool = get_pg()
    active_filter = "AND active = true" if active_only else ""
    rows = await pool.fetch(
        f"""
        SELECT ad_id::text, advertiser_id, product_name, product_description,
               target_topics, creative_text, cta_url, bid_cpm,
               budget_remaining, active, created_at, updated_at
        FROM ads
        WHERE campaign_id = $1::uuid {active_filter}
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        campaign_id, limit, offset,
    )
    return [dict(r) for r in rows]


@router.patch("/ads/{ad_id}")
async def update_portal_ad(ad_id: str, payload: AdUpdatePayload):
    """Same logic as the admin endpoint, but under the portal prefix."""
    pool = get_pg()

    updates, params, idx = [], [], 1

    if payload.budget_remaining is not None:
        updates.append(f"budget_remaining = ${idx}")
        params.append(payload.budget_remaining)
        idx += 1
    if payload.active is not None:
        updates.append(f"active = ${idx}")
        params.append(payload.active)
        idx += 1
    if payload.creative_text is not None:
        updates.append(f"creative_text = ${idx}")
        params.append(payload.creative_text)
        idx += 1
    if payload.bid_cpm is not None:
        updates.append(f"bid_cpm = ${idx}")
        params.append(payload.bid_cpm)
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    updates.append("updated_at = NOW()")
    params.append(ad_id)
    set_clause = ", ".join(updates)

    result = await pool.execute(
        f"UPDATE ads SET {set_clause} WHERE ad_id = ${idx}::uuid",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Ad not found")

    return {"updated": ad_id}


@router.delete("/ads/{ad_id}")
async def delete_portal_ad(ad_id: str):
    pool = get_pg()
    result = await pool.execute(
        "UPDATE ads SET active = false, updated_at = NOW() WHERE ad_id = $1::uuid",
        ad_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"deleted": ad_id}


# ═══════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/campaigns/{campaign_id}/analytics",
    response_model=CampaignAnalyticsResponse,
)
async def campaign_analytics(
    campaign_id: str,
    days: int = Query(30, ge=1, le=90),
):
    """Per-campaign performance: totals + daily breakdown."""
    pool = get_pg()

    campaign = await pool.fetchrow(
        """
        SELECT campaign_id::text, name, status, total_budget, total_spent
        FROM campaigns WHERE campaign_id = $1::uuid
        """,
        campaign_id,
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # aggregate events for ads belonging to this campaign
    stats = await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE e.event_type = 'impression') AS impressions,
            COUNT(*) FILTER (WHERE e.event_type = 'click')      AS clicks,
            COUNT(*) FILTER (WHERE e.event_type = 'engagement')  AS engagements
        FROM events e
        JOIN ads a ON e.ad_id = a.ad_id
        WHERE a.campaign_id = $1::uuid
          AND e.created_at > NOW() - ($2 || ' days')::interval
        """,
        campaign_id, str(days),
    )

    impressions = stats["impressions"] or 0
    clicks = stats["clicks"] or 0
    engagements = stats["engagements"] or 0
    ctr = (clicks / impressions) if impressions > 0 else 0.0

    # daily breakdown from daily_spend_log
    daily_rows = await pool.fetch(
        """
        SELECT spend_date, impressions, clicks, engagements, spend
        FROM daily_spend_log
        WHERE campaign_id = $1::uuid
          AND spend_date > CURRENT_DATE - $2
        ORDER BY spend_date DESC
        """,
        campaign_id, days,
    )

    return CampaignAnalyticsResponse(
        campaign_id=campaign["campaign_id"],
        campaign_name=campaign["name"],
        status=campaign["status"],
        total_budget=float(campaign["total_budget"]),
        total_spent=float(campaign["total_spent"]),
        impressions=impressions,
        clicks=clicks,
        engagements=engagements,
        ctr=round(ctr, 4),
        daily_breakdown=[
            {
                "date": str(r["spend_date"]),
                "impressions": r["impressions"],
                "clicks": r["clicks"],
                "engagements": r["engagements"],
                "spend": float(r["spend"]),
            }
            for r in daily_rows
        ],
    )


@router.get(
    "/advertisers/{advertiser_id}/analytics",
    response_model=AdvertiserAnalyticsResponse,
)
async def advertiser_analytics(
    advertiser_id: str,
    days: int = Query(30, ge=1, le=90),
):
    """Rollup across all campaigns for a single advertiser."""
    pool = get_pg()

    adv = await pool.fetchrow(
        "SELECT advertiser_id, name FROM advertisers WHERE advertiser_id = $1",
        advertiser_id,
    )
    if not adv:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    # campaign summary
    campaign_rows = await pool.fetch(
        """
        SELECT campaign_id::text, name, status, total_budget, total_spent
        FROM campaigns
        WHERE advertiser_id = $1
        ORDER BY created_at DESC
        """,
        advertiser_id,
    )

    total_campaigns = len(campaign_rows)
    active_campaigns = sum(1 for c in campaign_rows if c["status"] == "active")
    total_budget = sum(float(c["total_budget"]) for c in campaign_rows)
    total_spent = sum(float(c["total_spent"]) for c in campaign_rows)

    # aggregate events across all ads owned by this advertiser
    stats = await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE e.event_type = 'impression') AS impressions,
            COUNT(*) FILTER (WHERE e.event_type = 'click')      AS clicks,
            COUNT(*) FILTER (WHERE e.event_type = 'engagement')  AS engagements
        FROM events e
        JOIN ads a ON e.ad_id = a.ad_id
        WHERE a.advertiser_id = $1
          AND e.created_at > NOW() - ($2 || ' days')::interval
        """,
        advertiser_id, str(days),
    )

    impressions = stats["impressions"] or 0
    clicks = stats["clicks"] or 0
    engagements = stats["engagements"] or 0
    ctr = (clicks / impressions) if impressions > 0 else 0.0

    return AdvertiserAnalyticsResponse(
        advertiser_id=adv["advertiser_id"],
        name=adv["name"],
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_spent=round(total_spent, 2),
        total_budget=round(total_budget, 2),
        impressions=impressions,
        clicks=clicks,
        engagements=engagements,
        ctr=round(ctr, 4),
        campaigns=[
            {
                "campaign_id": c["campaign_id"],
                "name": c["name"],
                "status": c["status"],
                "total_budget": float(c["total_budget"]),
                "total_spent": float(c["total_spent"]),
            }
            for c in campaign_rows
        ],
    )