"""
Admin API for ad management.  Temporary — gets replaced by a proper
advertiser portal later.  No auth yet (add before going to prod obv).

POST   /admin/ads           → bulk create
GET    /admin/ads           → list with filters
PATCH  /admin/ads/{ad_id}   → update budget / active / creative
DELETE /admin/ads/{ad_id}   → soft delete (sets active=false)
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.core.db import get_pg
from app.models.schemas import AdCreatePayload, AdUpdatePayload
from app.services.ai import embed_ad

log = structlog.get_logger()
router = APIRouter(prefix="/admin/ads", tags=["admin"])


@router.post("")
async def bulk_create_ads(ads: list[AdCreatePayload]):
    """
    Insert a batch of ads.  For each ad we compute the embedding vector
    by calling the AI teammate's embed_ad() — or the mock if we're in
    mock mode.
    """
    pool = get_pg()
    created_ids = []

    for ad in ads:
        # build the text blob we embed (same concat the teammate expects)
        text_to_embed = f"{ad.product_name} {ad.product_description} {' '.join(ad.target_topics)}"
        embedding = await embed_ad(text_to_embed)
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        row = await pool.fetchrow(
            """
            INSERT INTO ads (
                advertiser_id, product_name, product_description,
                target_topics, target_intents, creative_text, cta_url,
                bid_cpm, budget_remaining, brand_safety_tags, embedding
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::vector)
            RETURNING ad_id::text
            """,
            ad.advertiser_id,
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
        log.info("admin.ad_created", ad_id=row["ad_id"], product=ad.product_name)

    return {"created": len(created_ids), "ad_ids": created_ids}


@router.get("")
async def list_ads(
    active_only: bool = Query(True),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    pool = get_pg()
    where = "WHERE active = true" if active_only else ""
    rows = await pool.fetch(
        f"""
        SELECT ad_id::text, advertiser_id, product_name, bid_cpm,
               budget_remaining, active, created_at
        FROM ads {where}
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


@router.patch("/{ad_id}")
async def update_ad(ad_id: str, payload: AdUpdatePayload):
    pool = get_pg()

    # build the SET clause dynamically based on what the caller sent
    updates = []
    params = []
    idx = 1

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
    set_clause = ", ".join(updates)
    params.append(ad_id)

    result = await pool.execute(
        f"UPDATE ads SET {set_clause} WHERE ad_id = ${idx}::uuid",
        *params,
    )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Ad not found")

    return {"updated": ad_id}


@router.delete("/{ad_id}")
async def delete_ad(ad_id: str):
    """Soft delete — just flip active to false so analytics still work."""
    pool = get_pg()
    result = await pool.execute(
        "UPDATE ads SET active = false, updated_at = NOW() WHERE ad_id = $1::uuid",
        ad_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"deleted": ad_id}
