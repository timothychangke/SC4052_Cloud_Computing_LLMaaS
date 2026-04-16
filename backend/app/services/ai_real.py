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
    EngagementMetrics, EngagementType,
)
_CONTEXT_MODEL = "openai/gpt-oss-20b"
_CHAT_MODEL  = "openai/gpt-oss-120b"
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


async def warmup_embed_model() -> None:
    """Load and warm up the embedding model at startup to avoid first-request latency."""
    model = await asyncio.to_thread(SentenceTransformer, _EMBED_MODEL)
    await asyncio.to_thread(model.encode, "warmup")
    global _embed_model
    _embed_model = model



async def _embed(text: str) -> list[float]:
    """Encode text locally with sentence-transformers (768-dim, non-blocking)."""
    model = _get_embed_model()
    vec = await asyncio.to_thread(model.encode, text.replace("\n", " "))
    return vec.tolist()



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
        model=_CONTEXT_MODEL,
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



async def real_embed_query(context: ContextObject) -> list[float]:
    """Embed the query context as a 768-dim vector for pgvector search."""
    text = " ".join([
        context.intent.value,
        *context.topics,
        *context.entities,
        context.sentiment,
    ])
    return await _embed(text)



async def real_embed_ad(
    product_name: str,
    product_description: str,
    target_topics: list[str],
    target_intents: list[str],
) -> list[float]:
    """
    Extracts structured keywords from the ad via Groq (mirroring the schema
    that real_embed_query produces on the query side), then embeds those
    keywords.  Both sides of the cosine search now live in the same
    vocabulary space: intent + topics + entities + sentiment.
    """
    prompt = f"""Extract keywords from this advertisement for semantic ad-matching.
Return a JSON object with EXACTLY these fields — no extra text:

{{
  "intent": "<one of: product_research, comparison, purchase, general_question>",
  "topics": ["<topic1>", ...],
  "entities": ["<brand or product name>", ...],
  "sentiment": "<one of: positive, neutral>"
}}

Product name: {product_name}
Description: {product_description}
Target topics: {', '.join(target_topics)}
Target intents: {', '.join(target_intents)}"""

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    data = json.loads(raw)

    # Mirror real_embed_query exactly so both sides share the same vocabulary
    keyword_text = " ".join([
        data.get("intent", "product_research"),
        *data.get("topics", target_topics),
        *data.get("entities", [product_name]),
        data.get("sentiment", "positive"),
    ])
    return await _embed(keyword_text)



async def real_generate_initial_context(ad: Ad) -> str:
    """
    Generate the initial context.md for an ad based on its static fields.
    Called once at ad creation time.
    """
    prompt = f"""You are an advertising strategist for a conversational AI platform.
Given the following ad details, write a concise context guide (3-5 bullet points)
that will help an AI assistant naturally recommend this product in conversation.

Focus on:
- The most compelling angle to introduce this product
- The tone and framing that would feel natural (not salesy)
- Key differentiators to highlight
- What user intents/situations this product is best suited for
- What to avoid (e.g., don't oversell, don't compare negatively to competitors)

Ad Details:
- Product: {ad.product_name}
- Description: {ad.product_description}
- Creative Text: {ad.creative_text}
- Target Topics: {', '.join(ad.target_topics)}
- Target Intents: {', '.join(ad.target_intents)}

Return ONLY the context guide as plain text bullet points. No preamble."""

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()



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

        sponsored_block = (
            f"\n\nYou MUST include exactly one sponsored product mention in your response. "
            f"Format it as markdown: [Sponsored] The [{chosen_ad.product_name}]({url}) — <one compelling reason>. "
            f"Ad details — Product: {chosen_ad.product_name}. "
            f"Description: {chosen_ad.product_description}. "
            f"Creative: {chosen_ad.creative_text}."
        )

        ad_context = getattr(chosen_ad, 'ad_context', '') or ''
        if ad_context:
            sponsored_block += (
                f"\n\nPresentation guidance for this product:\n{ad_context}"
            )

        messages[0]["content"] += sponsored_block

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



async def real_extract_product_from_url(page_text: str) -> dict:
    """
    Uses Groq LLM to extract ad-ready product info from scraped webpage text.
    Returns a dict matching CampaignAdCreatePayload fields (minus cta_url/bid/budget).
    """
    prompt = f"""You are an ad creation assistant. Extract product information from the following webpage content.
Return a JSON object with EXACTLY these fields — no extra text:

{{
  "product_name": "<product name>",
  "product_description": "<1-2 sentence product description>",
  "creative_text": "<compelling ad copy, 1-2 sentences>",
  "target_topics": ["<topic1>", "<topic2>"],
  "target_intents": ["<one of: product_research, comparison, purchase, general_question>"],
  "brand_safety_tags": ["<tag1>", "<tag2>"]
}}

Webpage content:
{page_text[:8000]}"""

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    return json.loads(raw)



async def _build_product_placement_prompt(user_prompt: str, ad: Ad) -> str:
    """
    Uses Groq to rewrite the user's image prompt so that the advertised
    product is organically placed in the scene.
    """
    prompt = f"""You are an expert image-prompt engineer for an advertising platform.
A user wants to generate an image. Your job is to rewrite their prompt so the
advertised product appears naturally in the scene — visible but not forced.

User's original prompt: {user_prompt}

Product to place: {ad.product_name}
Product description: {ad.product_description}

Rules:
- Keep the core scene the user described.
- Add the product in a way that fits the environment (e.g., on a shelf, in someone's hand, on a table, being worn by someone).
- Keep the rewritten prompt under 200 words.
- Return ONLY the rewritten image prompt, no explanation or preamble."""

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


async def real_generate_image(prompt: str, ad: Ad | None) -> dict:
    """
    Builds a product-placement prompt via Groq (when an ad is available),
    then generates the image with gpt-image-1.

    If the ad has a product_image_url, downloads it and passes it as a
    reference image via images.edit so the model can visually ground the
    product in the generated scene.  Falls back to images.generate when
    no product image is present or the download fails.

    gpt-image-1 returns base64 (no URL), so we convert it to a data URI.
    Returns {"image_url": str, "enhanced_prompt": str}.
    """
    import io
    import httpx
    from openai import AsyncOpenAI

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    enhanced_prompt = prompt
    if ad:
        enhanced_prompt = await _build_product_placement_prompt(prompt, ad)

    if ad and ad.product_image_url:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                img_resp = await http.get(ad.product_image_url)
                img_resp.raise_for_status()
                img_bytes = img_resp.content

            img_file = io.BytesIO(img_bytes)
            img_file.name = "product.png"

            response = await client.images.edit(
                model="gpt-image-1",
                image=img_file,
                prompt=enhanced_prompt,
                n=1,
                quality='high',
                size="1024x1024",
            )
            print("Use Product Image URL")
        except Exception:
            # fall back to plain generation if download or edit fails
            response = await client.images.generate(
                model="gpt-image-1",
                prompt=enhanced_prompt,
                n=1,
                size="1024x1024",
                quality="low",
            )
            print("Generate image from scratch")

    else:
        print("No product URL")
        response = await client.images.generate(
            model="gpt-image-1",
            prompt=enhanced_prompt,
            n=1,
            size="1024x1024",
            quality="low",
        )
        print("Generate image from scratch")

    b64 = response.data[0].b64_json
    image_url = f"data:image/png;base64,{b64}"

    return {
        "image_url": image_url,
        "enhanced_prompt": enhanced_prompt,
    }



async def real_detect_engagement(
    follow_up_message: str,
    shown_ad: Ad,
    assistant_response: str = "",
    history: list[Turn] | None = None,
) -> EngagementMetrics:
    """
    Asks Groq LLM to evaluate detailed engagement metrics
    for the user's follow-up after a sponsored ad was shown.
    """
    history_snippet = ""
    if history:
        history_snippet = "\n".join(
            f"{t.role}: {t.content}" for t in history[-4:]
        )

    prompt = f"""Analyse whether the user engaged with the advertised product in their follow-up message.

    Advertised product: {shown_ad.product_name}
    Product description: {shown_ad.product_description}

    {"Assistant response that contained the ad:" if assistant_response else ""}
    {assistant_response}

    {"Recent conversation context:" if history_snippet else ""}
    {history_snippet}

    User's follow-up message: {follow_up_message}

    Return a JSON object with EXACTLY these fields — no extra text:

    {{
      "engaged": <true or false>,
      "engagement_type": "<one of: product_inquiry, comparison, price_inquiry, purchase_intent, feature_question, positive_reaction, negative_reaction, dismissal, none>",
      "engagement_score": <float 0.0-1.0, how strongly the user engaged>,
      "sentiment_toward_ad": "<one of: positive, neutral, negative>",
      "ad_naturalness_score": <float 0.0-1.0, how natural/non-intrusive the ad felt based on user reaction>,
      "purchase_proximity": <float 0.0-1.0, how close the user seems to making a purchase>,
      "follow_up_topic_match": <true if user stayed on the product topic, false otherwise>,
      "reasoning": "<one sentence explaining your assessment>"
    }}"""

    resp = await _get_groq().chat.completions.create(
        model=_CHAT_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    data = json.loads(raw)

    return EngagementMetrics(
        engaged=bool(data.get("engaged", False)),
        engagement_type=EngagementType(data.get("engagement_type", "none")),
        engagement_score=float(data.get("engagement_score", 0.0)),
        sentiment_toward_ad=data.get("sentiment_toward_ad", "neutral"),
        ad_naturalness_score=float(data.get("ad_naturalness_score", 0.5)),
        purchase_proximity=float(data.get("purchase_proximity", 0.0)),
        follow_up_topic_match=bool(data.get("follow_up_topic_match", False)),
        reasoning=data.get("reasoning", ""),
    )
