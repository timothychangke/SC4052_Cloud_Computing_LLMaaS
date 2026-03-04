"""
Mock implementations of every AI/LLM contract.

These exist so the backend can be developed and tested end-to-end
before the teammate's real modules are ready.  Flip AI_MODULE_MODE
from "mock" to "real" in .env once the teammate delivers.

Each mock mirrors the exact signature from interface-contracts.md.
"""

from __future__ import annotations

import random
from app.models.schemas import (
    Ad, ContextObject, Intent, AdReceptivity, ResponseObject, Turn,
)


# ── Contract 1: Context Extraction ──────────────────────────────────────

async def mock_extract_context(message: str, history: list[Turn]) -> ContextObject:
    """
    Pretends to understand the message.  Returns canned values that
    exercise the happy path (product research, high receptivity).
    """
    return ContextObject(
        intent=Intent.PRODUCT_RESEARCH,
        topics=["running shoes"],
        entities=["Nike"],
        sentiment="positive",
        purchase_signal=0.7,
        ad_receptivity=AdReceptivity.HIGH,
    )


# ── Contract 2: Query Embedding ─────────────────────────────────────────

async def mock_embed_query(context: ContextObject) -> list[float]:
    """Return a random 1536-dim vector.  Good enough for wiring tests."""
    return [random.uniform(-1, 1) for _ in range(1536)]


# ── Contract 3: Ad Embedding (ingestion time) ───────────────────────────

async def mock_embed_ad(text: str) -> list[float]:
    """Same idea — random vector so we can test the ingestion pipeline."""
    return [random.uniform(-1, 1) for _ in range(1536)]


# ── Contract 5: Response Synthesis ──────────────────────────────────────

async def mock_generate_response(
    message: str,
    history: list[Turn],
    context: ContextObject,
    ads: list[Ad],
    tracking_urls: dict[str, str],
) -> ResponseObject:
    """
    Builds a canned response that includes the top ad if there is one.
    The formatting matches what the real module should produce so the
    frontend parsing logic can be tested against this.
    """
    if ads:
        ad = ads[0]
        url = tracking_urls.get(ad.ad_id, ad.cta_url)
        text = (
            f"Great question! Here's what I found. "
            f"[Sponsored] The [{ad.product_name}]({url}) is a solid choice — "
            f"{ad.product_description} "
            f"Let me know if you'd like to compare with other options!"
        )
        return ResponseObject(
            response_text=text,
            ad_included=True,
            ad_id_used=ad.ad_id,
        )

    return ResponseObject(
        response_text="Here's a helpful response to your question. Let me know if you need anything else!",
        ad_included=False,
        ad_id_used=None,
    )


# ── Contract 6: Engagement Detection ────────────────────────────────────

async def mock_detect_engagement(follow_up_message: str, shown_ad: Ad) -> bool:
    """
    Dead-simple keyword check.  The real version might use an LLM call,
    but this is fine for testing the engagement logging pipeline.
    """
    msg_lower = follow_up_message.lower()
    product_words = shown_ad.product_name.lower().split()
    return any(word in msg_lower for word in product_words if len(word) > 2)
