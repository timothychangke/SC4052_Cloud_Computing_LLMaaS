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
    EngagementMetrics, EngagementType,
)

# ── Context Extraction ──────────────────────────────────────

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


# ── Query Embedding ─────────────────────────────────────────

async def mock_embed_query(context: ContextObject) -> list[float]:
    """Return a random 1536-dim vector.  Good enough for wiring tests."""
    return [random.uniform(-1, 1) for _ in range(1536)]


# ── Ad Embedding (ingestion time) ───────────────────────────

async def mock_embed_ad(
    product_name: str,
    product_description: str,
    target_topics: list[str],
    target_intents: list[str],
) -> list[float]:
    """Same idea — random vector so we can test the ingestion pipeline."""
    return [random.uniform(-1, 1) for _ in range(1536)]

# ── Initial Context Generation (mock) ─────────────────────────

async def mock_generate_initial_context(ad: Ad) -> str:
    """Return a canned context guide for testing."""
    return (
        f"• Lead with {ad.product_name}'s key differentiator in a helpful, conversational tone\n"
        f"• Best suited when user is researching or comparing products in this category\n"
        f"• Emphasize genuine value — don't oversell or use hyperbolic language\n"
        f"• Avoid negative comparisons with competitor products\n"
        f"• Keep the mention brief and integrated into the broader helpful response"
    )


# ── Response Synthesis ──────────────────────────────────────

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


# ── Product Extraction from URL ─────────────────────────────

async def mock_extract_product_from_url(page_text: str) -> dict:
    """Returns canned product data for testing the extraction pipeline."""
    return {
        "product_name": "Sample Product",
        "product_description": "A high-quality product designed to meet your everyday needs.",
        "creative_text": "Discover the difference quality makes. Shop now and save!",
        "target_topics": ["shopping", "product"],
        "target_intents": ["product_research", "purchase"],
        "brand_safety_tags": ["general", "shopping"],
    }


# ── Image Generation ───────────────────────────────────────

async def mock_generate_image(prompt: str, ad: "Ad | None") -> dict:
    """
    Returns a placeholder image (picsum) with the product name woven into
    the enhanced prompt — mirrors what the real module produces.
    """
    enhanced_prompt = prompt
    if ad:
        f"{prompt}, with {ad.product_name} naturally featured in the scene"
    # Deterministic seed so the same prompt always returns the same placeholder
    seed = abs(hash(prompt)) % 1000
    return {
        "image_url": f"https://picsum.photos/seed/{seed}/1024/576",
        "enhanced_prompt": enhanced_prompt,
    }


# ── Engagement Detection ────────────────────────────────────

async def mock_detect_engagement(
    follow_up_message: str,
    shown_ad: Ad,
    assistant_response: str = "",
    history: list[Turn] | None = None,
) -> EngagementMetrics:
    """
    Keyword-based mock that returns full EngagementMetrics.
    """
    msg_lower = follow_up_message.lower()
    product_words = shown_ad.product_name.lower().split()
    engaged = any(word in msg_lower for word in product_words if len(word) > 2)

    return EngagementMetrics(
        engaged=engaged,
        engagement_type=EngagementType.PRODUCT_INQUIRY if engaged else EngagementType.NONE,
        engagement_score=0.8 if engaged else 0.1,
        sentiment_toward_ad="positive" if engaged else "neutral",
        ad_naturalness_score=0.7,
        purchase_proximity=0.5 if engaged else 0.1,
        follow_up_topic_match=engaged,
        reasoning="Mock: keyword match" if engaged else "Mock: no keyword match",
    )
