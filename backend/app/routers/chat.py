"""
POST /chat  —  the main orchestrator endpoint.

This is where everything comes together:
  1. Load session from Redis
  2. Extract context (AI module)
  3. If receptive → embed query → retrieve ads → build tracking URLs
  4. Generate response (AI module), with or without ads
  5. Log impression if an ad was included
  6. Check engagement with previous ad (if one was shown last turn)
  7. Update session state
  8. Return response to the React frontend

Every AI module call is wrapped in a try/except so a failure in the
ad pipeline never blocks the user from getting a response.
"""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AdMetadata,
    AdReceptivity,
    ChatRequest,
    ChatResponse,
)
from app.services import ai, ads as ads_service, session as sess, tracking
from app.core.exceptions import (
    ContextExtractionError,
    EmbeddingError,
    ResponseGenerationError,
)
from app.models.schemas import Turn

log = structlog.get_logger()
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    t0 = time.monotonic()
    message = req.message
    session_id = req.session_id

    log.info("chat.start", session_id=session_id, message_len=len(message))

    # ── 1. Load session ──────────────────────────────────────────────
    session_data = await sess.get_session(session_id)
    history = sess.session_turns_to_domain(session_data)

    # ── 2. Check if previous turn had an ad → run engagement detection ─
    await _maybe_detect_engagement(message, session_data, session_id)

    # ── 3. Save the user's turn right away ───────────────────────────
    await sess.append_turn(session_id, role="user", content=message)

    # ── 4. Extract context ───────────────────────────────────────────
    context = None
    try:
        context = await ai.extract_context(message, history)
        log.info(
            "chat.context_extracted",
            intent=context.intent.value,
            receptivity=context.ad_receptivity.value,
            purchase_signal=context.purchase_signal,
        )
    except Exception as exc:
        # context extraction blew up — skip ads entirely, still give user a response
        log.warning("chat.context_extraction_failed", error=str(exc))

    # ── 5. Ad matching (only if context says we should) ──────────────
    candidate_ads = []
    tracking_urls: dict[str, str] = {}

    if context and context.ad_receptivity != AdReceptivity.NONE:
        try:
            query_vec = await ai.embed_query(context)
            candidate_ads = await ads_service.get_candidate_ads(query_vec, context, session_id)
            if candidate_ads:
                tracking_urls = tracking.generate_tracking_urls(candidate_ads, session_id)
        except EmbeddingError as exc:
            log.warning("chat.embedding_failed", error=str(exc))
        except Exception as exc:
            # something unexpected in the ad pipeline — log it, keep going
            log.error("chat.ad_matching_failed", error=str(exc), exc_info=True)

    # ── 6. Generate the response ─────────────────────────────────────
    response_obj = None
    retry_count = 0

    while response_obj is None and retry_count < 2:
        try:
            response_obj = await ai.generate_response(
                message=message,
                history=history,
                context=context,
                ads=candidate_ads,
                tracking_urls=tracking_urls,
            )
        except Exception as exc:
            retry_count += 1
            log.warning("chat.response_generation_failed", attempt=retry_count, error=str(exc))
            if retry_count >= 2:
                # give up on ads, try one last time with no sponsored context
                try:
                    response_obj = await ai.generate_response(
                        message=message,
                        history=history,
                        context=context,
                        ads=[],
                        tracking_urls={},
                    )
                except Exception:
                    # absolute last resort — something is seriously wrong
                    log.error("chat.total_generation_failure", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail="Sorry, something went wrong generating a response.",
                    )

    # ── 7. Log impression + update session ───────────────────────────
    ad_meta = None
    ad_id_for_turn = None

    if response_obj.ad_included and response_obj.ad_id_used:
        ad_id_for_turn = response_obj.ad_id_used
        ad_meta = AdMetadata(ad_id=ad_id_for_turn, sponsored=True)

        try:
            turn_number = session_data.get("turn_count", 0) + 1
            await tracking.log_impression(session_id, ad_id_for_turn, turn_number)
            await sess.record_ad_shown(session_id, ad_id_for_turn)
        except Exception as exc:
            # impression logging shouldn't block the response
            log.error("chat.impression_logging_failed", error=str(exc))

    # update accumulated topics / purchase signals if we got context
    if context:
        try:
            await sess.update_topics_and_signals(
                session_id, context.topics, context.purchase_signal
            )
        except Exception as exc:
            log.warning("chat.session_update_failed", error=str(exc))

    # save the assistant's turn
    await sess.append_turn(
        session_id, role="assistant", content=response_obj.response_text, ad_id=ad_id_for_turn
    )

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    log.info(
        "chat.done",
        session_id=session_id,
        ad_included=response_obj.ad_included,
        elapsed_ms=elapsed_ms,
    )

    return ChatResponse(response=response_obj.response_text, ad_metadata=ad_meta)


# ── Helper: engagement detection for the previous turn's ad ─────────────

async def _maybe_detect_engagement(
    current_message: str,
    session_data: dict,
    session_id: str,
):
    """
    If the previous assistant turn included an ad, check whether
    the user's new message engages with that product.
    """
    turns = session_data.get("turns", [])
    if len(turns) < 1:
        return

    last_turn = turns[-1]
    if last_turn.get("role") != "assistant" or not last_turn.get("ad_id"):
        return  # no ad was shown last turn

    ad_id = last_turn["ad_id"]

    try:
        # we need the Ad object to pass to the engagement detector
        # quick fetch from the DB
        from app.core.db import get_pg
        row = await get_pg().fetchrow(
            """
            SELECT ad_id::text, advertiser_id, product_name, product_description,
                   target_topics, target_intents, creative_text, cta_url,
                   bid_cpm, budget_remaining, brand_safety_tags,
                   ad_context, ad_context_version
            FROM ads WHERE ad_id = $1::uuid
            """,
            ad_id,
        )
        if not row:
            return

        from app.models.schemas import Ad
        shown_ad = Ad(
            ad_id=row["ad_id"],
            advertiser_id=row["advertiser_id"],
            product_name=row["product_name"],
            product_description=row["product_description"] or "",
            target_topics=row["target_topics"] or [],
            target_intents=row["target_intents"] or [],
            creative_text=row["creative_text"],
            cta_url=row["cta_url"],
            bid_cpm=float(row["bid_cpm"]),
            budget_remaining=float(row["budget_remaining"]),
            brand_safety_tags=row["brand_safety_tags"] or [],
            ad_context=row["ad_context"] or "",
            ad_context_version=row["ad_context_version"] or 0,
        )

        metrics = await ai.detect_engagement(
            current_message,
            shown_ad,
            assistant_response=last_turn.get("content", ""),
            history=[
                Turn(
                    role=t["role"],
                    content=t["content"],
                    timestamp=t.get("timestamp", ""),
                    ad_id=t.get("ad_id"),
                )
                for t in turns[-4:]
            ],
        )
        if metrics.engaged:
            await tracking.log_engagement(session_id, ad_id, current_message, metrics=metrics)
            log.info(
                "chat.engagement_detected",
                session_id=session_id,
                ad_id=ad_id,
                engagement_type=metrics.engagement_type.value,
                engagement_score=metrics.engagement_score,
            )

    except Exception as exc:
        # engagement detection is nice-to-have — never crash the request over it
        log.warning("chat.engagement_detection_failed", error=str(exc))
