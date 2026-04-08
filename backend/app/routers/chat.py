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
    ImageGenerateRequest,
    ImageGenerateResponse,
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

    print(f"\n{'='*60}")
    print(f"[1/7] CHAT REQUEST  session={session_id}")
    print(f"      message: {message[:120]}")
    print(f"{'='*60}")

    # ── 1. Load session ──────────────────────────────────────────────
    session_data = await sess.get_session(session_id)
    history = sess.session_turns_to_domain(session_data)
    print(f"[1/7] Session loaded  turns={len(history)}")

    # ── 2. Check if previous turn had an ad → run engagement detection ─
    print(f"[2/7] Checking engagement with previous ad...")
    await _maybe_detect_engagement(message, session_data, session_id)

    # ── 3. Save the user's turn right away ───────────────────────────
    await sess.append_turn(session_id, role="user", content=message)
    print(f"[3/7] User turn saved")

    # ── 4. Extract context ───────────────────────────────────────────
    print(f"[4/7] Extracting context...")
    context = None
    try:
        context = await ai.extract_context(message, history)
        print(f"      intent={context.intent.value}  receptivity={context.ad_receptivity.value}  purchase_signal={context.purchase_signal:.2f}")
        print(f"      topics={context.topics}  entities={context.entities}")
        log.info(
            "chat.context_extracted",
            intent=context.intent.value,
            receptivity=context.ad_receptivity.value,
            purchase_signal=context.purchase_signal,
        )
    except Exception as exc:
        print(f"      [WARN] context extraction failed: {exc}")
        log.warning("chat.context_extraction_failed", error=str(exc))

    # ── 5. Ad matching (only if context says we should) ──────────────
    candidate_ads = []
    tracking_urls: dict[str, str] = {}

    if context and context.ad_receptivity != AdReceptivity.NONE:
        print(f"[5/7] Ad matching (receptivity={context.ad_receptivity.value})...")
        try:
            query_vec = await ai.embed_query(context)
            print(f"      Query embedded  dims={len(query_vec)}")
            candidate_ads = await ads_service.get_candidate_ads(query_vec, context, session_id)
            print(f"      Candidates found: {len(candidate_ads)}")
            for ad in candidate_ads[:3]:
                print(f"        • {ad.product_name}  score={getattr(ad, 'score', 'n/a')}")
            if candidate_ads:
                tracking_urls = tracking.generate_tracking_urls(candidate_ads, session_id)
                print(f"      Tracking URLs built for {len(tracking_urls)} ad(s)")
        except EmbeddingError as exc:
            print(f"      [WARN] embedding failed: {exc}")
            log.warning("chat.embedding_failed", error=str(exc))
        except Exception as exc:
            print(f"      [ERROR] ad matching failed: {exc}")
            log.error("chat.ad_matching_failed", error=str(exc), exc_info=True)
    else:
        print(f"[5/7] Ad matching skipped  (receptivity={getattr(context, 'ad_receptivity', 'no-context')})")

    # ── 6. Generate the response ─────────────────────────────────────
    print(f"[6/7] Generating response  ads_available={len(candidate_ads)}...")
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
            print(f"      [WARN] generation attempt {retry_count} failed: {exc}")
            log.warning("chat.response_generation_failed", attempt=retry_count, error=str(exc))
            if retry_count >= 2:
                print(f"      Retrying without ads...")
                try:
                    response_obj = await ai.generate_response(
                        message=message,
                        history=history,
                        context=context,
                        ads=[],
                        tracking_urls={},
                    )
                except Exception:
                    log.error("chat.total_generation_failure", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail="Sorry, something went wrong generating a response.",
                    )

    print(f"      ad_included={response_obj.ad_included}  ad_id={response_obj.ad_id_used}")

    # ── 7. Log impression + update session ───────────────────────────
    print(f"[7/7] Logging impression and updating session...")
    ad_meta = None
    ad_id_for_turn = None

    if response_obj.ad_included and response_obj.ad_id_used:
        ad_id_for_turn = response_obj.ad_id_used
        ad_meta = AdMetadata(ad_id=ad_id_for_turn, sponsored=True)
        try:
            turn_number = session_data.get("turn_count", 0) + 1
            await tracking.log_impression(session_id, ad_id_for_turn, turn_number)
            await sess.record_ad_shown(session_id, ad_id_for_turn)
            print(f"      Impression logged  ad_id={ad_id_for_turn}")
        except Exception as exc:
            print(f"      [ERROR] impression logging failed: {exc}")
            log.error("chat.impression_logging_failed", error=str(exc))

    if context:
        try:
            await sess.update_topics_and_signals(
                session_id, context.topics, context.purchase_signal
            )
        except Exception as exc:
            log.warning("chat.session_update_failed", error=str(exc))

    await sess.append_turn(
        session_id, role="assistant", content=response_obj.response_text, ad_id=ad_id_for_turn
    )

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    print(f"      Done  elapsed={elapsed_ms}ms")
    print(f"{'='*60}\n")
    log.info("chat.done", session_id=session_id, ad_included=response_obj.ad_included, elapsed_ms=elapsed_ms)

    return ChatResponse(response=response_obj.response_text, ad_metadata=ad_meta)


# ── Image generation with product placement ──────────────────────────────

@router.post("/generate-image", response_model=ImageGenerateResponse)
async def generate_image(req: ImageGenerateRequest):
    t0 = time.monotonic()
    prompt = req.prompt
    session_id = req.session_id

    print(f"\n{'='*60}")
    print(f"[1/5] IMAGE GENERATION REQUEST  session={session_id}")
    print(f"      prompt: {prompt[:120]}")
    print(f"{'='*60}")

    # ── 1. Load session ──────────────────────────────────────────────
    session_data = await sess.get_session(session_id)
    history = sess.session_turns_to_domain(session_data)
    print(f"[1/5] Session loaded  turns={len(history)}")

    # ── 2. Extract context for ad matching ──────────────────────────
    print(f"[2/5] Extracting context from prompt...")
    context = None
    try:
        context = await ai.extract_context(prompt, history)
        print(f"      intent={context.intent.value}  receptivity={context.ad_receptivity.value}")
        print(f"      topics={context.topics}")
    except Exception as exc:
        print(f"      [WARN] context extraction failed: {exc}")
        log.warning("generate_image.context_extraction_failed", error=str(exc))

    # ── 3. Ad matching ───────────────────────────────────────────────
    chosen_ad = None
    if context :
        print(f"[3/5] Ad matching for product placement...")
        try:
            query_vec = await ai.embed_query(context)
            print(f"      Query embedded  dims={len(query_vec)}")
            candidate_ads = await ads_service.get_candidate_ads(query_vec, context, session_id)
            print(f"      Candidates found: {len(candidate_ads)}")
            if candidate_ads:
                chosen_ad = candidate_ads[0]
                print(f"      Selected ad: {chosen_ad.product_name}  id={chosen_ad.ad_id}")
            else:
                print(f"      No matching ads — generating without product placement")
        except Exception as exc:
            print(f"      [WARN] ad matching failed: {exc}")
            log.warning("generate_image.ad_matching_failed", error=str(exc))
    else:
        print(f"[3/5] Ad matching skipped  (receptivity={getattr(context, 'ad_receptivity', 'no-context')})")

    # ── 4. Generate image (with product placement if ad matched) ─────
    print(f"[4/5] Generating image  product_placement={chosen_ad is not None}...")
    try:
        result = await ai.generate_image(prompt, chosen_ad)
        print(f"      Enhanced prompt: {result['enhanced_prompt'][:120]}")
        # print(f"      Image URL: {result['image_url']}")
    except Exception as exc:
        print(f"      [ERROR] image generation failed: {exc}")
        log.error("generate_image.generation_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Image generation failed.")

    # ── 5. Log impression + return ───────────────────────────────────
    print(f"[5/5] Logging impression and returning response...")
    ad_meta = None
    if chosen_ad:
        ad_meta = AdMetadata(ad_id=chosen_ad.ad_id, sponsored=True)
        try:
            turn_number = session_data.get("turn_count", 0) + 1
            await tracking.log_impression(session_id, chosen_ad.ad_id, turn_number)
            await sess.record_ad_shown(session_id, chosen_ad.ad_id)
            print(f"      Impression logged  ad_id={chosen_ad.ad_id}")
        except Exception as exc:
            print(f"      [ERROR] impression logging failed: {exc}")
            log.error("generate_image.impression_logging_failed", error=str(exc))

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    print(f"      Done  elapsed={elapsed_ms}ms")
    print(f"{'='*60}\n")
    log.info("generate_image.done", session_id=session_id, ad_included=chosen_ad is not None)

    return ImageGenerateResponse(
        image_url=result["image_url"],
        enhanced_prompt=result["enhanced_prompt"],
        ad_metadata=ad_meta,
    )


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
