"""
Thin dispatcher that picks the right implementation (mock vs real)
based on AI_MODULE_MODE in config.

When the AI teammate delivers their modules, drop them into
app/services/ai_real.py with the same function signatures and
flip the env var.  Nothing else in the codebase needs to change.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.models.schemas import Ad, ContextObject, EngagementMetrics, ResponseObject, Turn


async def extract_context(message: str, history: list[Turn]) -> ContextObject:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_extract_context
        return await real_extract_context(message, history)
    else:
        from app.services.ai_mock import mock_extract_context
        return await mock_extract_context(message, history)


async def embed_query(context: ContextObject) -> list[float]:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_embed_query
        return await real_embed_query(context)
    else:
        from app.services.ai_mock import mock_embed_query
        return await mock_embed_query(context)


async def embed_ad(
    product_name: str,
    product_description: str,
    target_topics: list[str],
    target_intents: list[str],
) -> list[float]:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_embed_ad
        return await real_embed_ad(product_name, product_description, target_topics, target_intents)
    else:
        from app.services.ai_mock import mock_embed_ad
        return await mock_embed_ad(product_name, product_description, target_topics, target_intents)


async def generate_response(
    message: str,
    history: list[Turn],
    context: ContextObject,
    ads: list[Ad],
    tracking_urls: dict[str, str],
) -> ResponseObject:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_generate_response
        return await real_generate_response(message, history, context, ads, tracking_urls)
    else:
        from app.services.ai_mock import mock_generate_response
        return await mock_generate_response(message, history, context, ads, tracking_urls)


async def extract_product_from_url(page_text: str) -> dict:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_extract_product_from_url
        return await real_extract_product_from_url(page_text)
    else:
        from app.services.ai_mock import mock_extract_product_from_url
        return await mock_extract_product_from_url(page_text)


async def detect_engagement(
    follow_up_message: str,
    shown_ad: Ad,
    assistant_response: str = "",
    history: list[Turn] | None = None,
) -> EngagementMetrics:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_detect_engagement
        return await real_detect_engagement(follow_up_message, shown_ad, assistant_response, history)
    else:
        from app.services.ai_mock import mock_detect_engagement
        return await mock_detect_engagement(follow_up_message, shown_ad, assistant_response, history)

async def generate_image(prompt: str, ad: "Ad | None") -> dict:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_generate_image
        return await real_generate_image(prompt, ad)
    else:
        from app.services.ai_mock import mock_generate_image
        return await mock_generate_image(prompt, ad)


async def generate_initial_context(ad: Ad) -> str:
    settings = get_settings()
    if settings.ai_module_mode == "real":
        from app.services.ai_real import real_generate_initial_context
        return await real_generate_initial_context(ad)
    else:
        from app.services.ai_mock import mock_generate_initial_context
        return await mock_generate_initial_context(ad)
