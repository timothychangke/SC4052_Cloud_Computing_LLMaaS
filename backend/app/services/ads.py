"""
Ad retrieval pipeline (Contract 4 — owned by backend).

Steps:
  1. pgvector cosine similarity search → top 20 raw candidates
  2. Filter out inactive ads, zero-budget ads, already-shown-this-session ads
  3. Score: similarity*0.5 + normalised_bid*0.3 + purchase_signal*0.2
  4. Return top 3

This is the only Contract the backend owns; everything else is the
AI teammate's territory and we just call into their modules.
"""

from __future__ import annotations

import structlog

from app.core.db import get_pg
from app.models.schemas import Ad, ContextObject
from app.services.session import get_session

log = structlog.get_logger()


async def get_candidate_ads(
    query_embedding: list[float],
    context: ContextObject,
    session_id: str,
) -> list[Ad]:
    """
    Main entry point.  Returns up to 3 ranked Ad objects.
    Returns an empty list if nothing suitable is found — the orchestrator
    handles that gracefully (just generates a response with no ad).
    """
    pool = get_pg()

    # -- Step 1: vector similarity search (top 20) --
    # pgvector's <=> operator is cosine distance, so similarity = 1 - distance
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    rows = await pool.fetch(
        """
        SELECT
            ad_id::text,
            advertiser_id,
            product_name,
            product_description,
            target_topics,
            target_intents,
            creative_text,
            cta_url,
            bid_cpm,
            budget_remaining,
            brand_safety_tags,
            1 - (embedding <=> $1::vector) AS similarity
        FROM ads
        WHERE active = true
          AND budget_remaining > 0
        ORDER BY embedding <=> $1::vector
        LIMIT 20
        """,
        embedding_str,
    )

    if not rows:
        log.info("ad_retrieval.no_raw_candidates")
        return []

    # -- Step 2: filter out ads we already showed this session --
    session = await get_session(session_id)
    shown_ids = set(session.get("ads_shown_this_session", []))

    candidates: list[Ad] = []
    for r in rows:
        if r["ad_id"] in shown_ids:
            continue  # frequency cap
        candidates.append(
            Ad(
                ad_id=r["ad_id"],
                advertiser_id=r["advertiser_id"],
                product_name=r["product_name"],
                product_description=r["product_description"] or "",
                target_topics=r["target_topics"] or [],
                target_intents=r["target_intents"] or [],
                creative_text=r["creative_text"],
                cta_url=r["cta_url"],
                bid_cpm=float(r["bid_cpm"]),
                budget_remaining=float(r["budget_remaining"]),
                brand_safety_tags=r["brand_safety_tags"] or [],
                similarity=float(r["similarity"]),
            )
        )

    if not candidates:
        log.info("ad_retrieval.all_filtered_out", shown_ids=list(shown_ids))
        return []

    # -- Step 3: score with the agreed-upon formula --
    max_bid = max(c.bid_cpm for c in candidates) or 1.0
    for ad in candidates:
        ad.score = (
            ad.similarity * 0.5
            + (ad.bid_cpm / max_bid) * 0.3
            + context.purchase_signal * 0.2
        )

    # -- Step 4: return top 3 --
    candidates.sort(key=lambda a: a.score, reverse=True)
    top = candidates[:3]

    log.info(
        "ad_retrieval.done",
        raw_count=len(rows),
        after_filter=len(candidates),
        returned=len(top),
        top_score=round(top[0].score, 3) if top else None,
    )
    return top
