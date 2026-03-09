"""
Real implementations of every AI/LLM contract.

LLM  (context extraction, response generation, engagement detection):
  Groq -- llama-3.3-70b-versatile         set GROQ_API_KEY in .env

Embeddings (query + ad ingestion):
  sentence-transformers/all-mpnet-base-v2 (768-dim, runs locally)
  Model downloads automatically on first use (~420 MB).
  The Postgres column is vector(768) to match.
"""

from __future__ import annotations

import asyncio
import json

from groq import AsyncGroq
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.models.schemas import (
    Ad, ContextObject, Intent, AdReceptivity, ResponseObject, Turn,
)

_CHAT_MODEL  = "llama-3.3-70b-versatile"
_EMBED_MODEL = "all-mpnet-base-v2"

_groq_client: AsyncGroq | None = None
_embed_model: SentenceTransformer | None = None


def _get_groq() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _groq_client


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(_EMBED_MODEL)
    return _embed_model


# Embedding helper

async def _embed(text: str) -> list[float]:
    """Encode text locally with sentence-transformers (768-dim, non-blocking)."""
    model = _get_embed_model()
    vec = await asyncio.to_thread(model.encode, text.replace("\n", " "))
    return vec.tolist()


# ── Contract 1: Context Extraction ──────────────────────────────────────

async def real_extract_context(message: str, history: list[Turn]) -> ContextObject:
    """
    Uses Groq LLM to classify intent, extract topics/entities, gauge sentiment,
    estimate purchase likelihood, and determine ad receptivity.
    """
    history_text = "\n".join(
        f"{t.role}: {t.content}" for t in history[-6:]
    ) or "(no prior conversation)"

    prompt = f"""Analyse the conversation below and the latest user message.
Return a JSON object with EXACTLY these fields — no extra text:

{{
  "intent": "<one of: product_research, comparison, purchase, general_question, casual_chat, support, complaint, sensitive>",
  "topics": ["<topic1>", ...],
  "entities": ["<brand or product name>", ...],
  "sentiment": "<one of: positive, neutral, negative, mixed>",
  "purchase_signal": <float 0.0-1.0>,
  "ad_receptivity": "<one of: high, medium, low, none>"
}}

Conversation history:
{history_text}

Latest user message: {message}"""

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.choices[0].message.content.strip()
    # strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    data = json.loads(raw)

    return ContextObject(
        intent=Intent(data.get("intent", "general_question")),
        topics=data.get("topics", []),
        entities=data.get("entities", []),
        sentiment=data.get("sentiment", "neutral"),
        purchase_signal=float(data.get("purchase_signal", 0.3)),
        ad_receptivity=AdReceptivity(data.get("ad_receptivity", "medium")),
    )


# ── Contract 2: Query Embedding ─────────────────────────────────────────

async def real_embed_query(context: ContextObject) -> list[float]:
    """Embed the query context as a 768-dim vector for pgvector search."""
    text = " ".join([
        context.intent.value,
        *context.topics,
        *context.entities,
        context.sentiment,
    ])
    return await _embed(text)


# ── Contract 3: Ad Embedding (ingestion time) ───────────────────────────

async def real_embed_ad(text: str) -> list[float]:
    """Embed ad creative text as a 768-dim vector for pgvector indexing."""
    return await _embed(text)


# ── Contract 5: Response Synthesis ──────────────────────────────────────

async def real_generate_response(
    message: str,
    history: list[Turn],
    context: ContextObject,
    ads: list[Ad],
    tracking_urls: dict[str, str],
) -> ResponseObject:
    """
    Generates a conversational reply via Groq LLM, weaving in a sponsored ad
    when ad_receptivity is high or medium and at least one ad is available.
    """
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful, friendly shopping and lifestyle assistant. "
                "Respond conversationally and helpfully. "
                "Keep replies concise (2-4 sentences). Use markdown where it helps."
            ),
        }
    ]

    for t in history[-8:]:
        messages.append({"role": t.role, "content": t.content})

    chosen_ad: Ad | None = None

    if ads and context.ad_receptivity in (AdReceptivity.HIGH, AdReceptivity.MEDIUM):
        chosen_ad = ads[0]
        url = tracking_urls.get(chosen_ad.ad_id, chosen_ad.cta_url)
        messages[0]["content"] += (
            f"\n\nYou MUST include exactly one sponsored product mention in your response. "
            f"Format it as markdown: [Sponsored] The [{chosen_ad.product_name}]({url}) — <one compelling reason>. "
            f"Ad details — Product: {chosen_ad.product_name}. "
            f"Description: {chosen_ad.product_description}. "
            f"Creative: {chosen_ad.creative_text}."
        )

    messages.append({"role": "user", "content": message})

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=1024,
        messages=messages,
    )

    response_text = resp.choices[0].message.content.strip()

    if chosen_ad:
        return ResponseObject(
            response_text=response_text,
            ad_included=True,
            ad_id_used=chosen_ad.ad_id,
        )

    return ResponseObject(
        response_text=response_text,
        ad_included=False,
        ad_id_used=None,
    )


# ── Contract 6: Engagement Detection ────────────────────────────────────

async def real_detect_engagement(follow_up_message: str, shown_ad: Ad) -> bool:
    """
    Asks Groq LLM whether the user's follow-up message indicates engagement
    with the previously shown sponsored product.
    """
    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=10,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Did the user show interest in or engage with the advertised product?\n\n"
                    f"Advertised product: {shown_ad.product_name}\n"
                    f"User's follow-up: {follow_up_message}\n\n"
                    f'Reply with exactly one word: "yes" or "no".'
                ),
            }
        ],
    )

    return resp.choices[0].message.content.strip().lower().startswith("yes")
