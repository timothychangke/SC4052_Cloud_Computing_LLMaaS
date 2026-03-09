"""
Quick smoke-test for ai_real.py (Groq backend).

Run from the backend/ directory with the venv active:
    python -m scripts.test_real
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  # picks up GROQ_API_KEY from .env

from app.models.schemas import Ad, Turn
from app.services.ai_real import (
    real_detect_engagement,
    real_embed_ad,
    real_embed_query,
    real_extract_context,
    real_generate_response,
)

# Fixtures

MESSAGE = "I'm looking for a good pair of running shoes under $150."

HISTORY = [
    Turn(role="user",      content="Hi, can you help me?",             timestamp="2024-01-01T00:00:00"),
    Turn(role="assistant", content="Of course! What are you looking for?", timestamp="2024-01-01T00:00:01"),
]

SAMPLE_AD = Ad(
    ad_id="ad-test-1",
    advertiser_id="nike",
    product_name="Nike Pegasus 41",
    product_description="Lightweight everyday trainer with React foam cushioning.",
    target_topics=["running", "shoes"],
    target_intents=["product_research", "purchase"],
    creative_text="Run farther, feel lighter. The Pegasus 41 is built for every mile.",
    cta_url="https://nike.com/pegasus-41",
    bid_cpm=5.0,
    budget_remaining=500.0,
    brand_safety_tags=[],
)

TRACKING_URLS = {"ad-test-1": "http://localhost:8000/track/click?ad=ad-test-1"}


# Helpers

def section(title):
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


def ok(label, value):
    print(f"  [OK] {label}: {value}")


# Tests

async def test_extract_context():
    section("Contract 1 - real_extract_context")
    ctx = await real_extract_context(MESSAGE, HISTORY)
    ok("intent",          ctx.intent.value)
    ok("topics",          ctx.topics)
    ok("entities",        ctx.entities)
    ok("sentiment",       ctx.sentiment)
    ok("purchase_signal", f"{ctx.purchase_signal:.2f}")
    ok("ad_receptivity",  ctx.ad_receptivity.value)
    return ctx


async def test_embed_query(ctx):
    section("Contract 2 - real_embed_query")
    vec = await real_embed_query(ctx)
    ok("dimensions",    len(vec))
    ok("first 4 values", [round(v, 4) for v in vec[:4]])
    assert len(vec) == 768, f"Expected 768 dims, got {len(vec)}"


async def test_embed_ad():
    section("Contract 3 - real_embed_ad")
    text = f"{SAMPLE_AD.product_name} {SAMPLE_AD.product_description} {SAMPLE_AD.creative_text}"
    vec = await real_embed_ad(text)
    ok("dimensions",     len(vec))
    ok("first 4 values", [round(v, 4) for v in vec[:4]])
    assert len(vec) == 768, f"Expected 768 dims, got {len(vec)}"


async def test_generate_response(ctx):
    section("Contract 5 - real_generate_response (with ad)")
    resp = await real_generate_response(MESSAGE, HISTORY, ctx, [SAMPLE_AD], TRACKING_URLS)
    ok("ad_included", resp.ad_included)
    ok("ad_id_used",  resp.ad_id_used)
    print(f"\n  Response:\n  {resp.response_text}\n")

    section("Contract 5 - real_generate_response (no ad)")
    resp2 = await real_generate_response(MESSAGE, HISTORY, ctx, [], {})
    ok("ad_included", resp2.ad_included)
    print(f"\n  Response:\n  {resp2.response_text}\n")


async def test_detect_engagement():
    section("Contract 6 - real_detect_engagement")
    engaged     = await real_detect_engagement("Tell me more about the Nike Pegasus", SAMPLE_AD)
    not_engaged = await real_detect_engagement("What is the weather like today?",     SAMPLE_AD)
    ok("related follow-up   -> engaged",     engaged)
    ok("unrelated follow-up -> not engaged", not not_engaged)


# Main

async def main():
    print("\nTesting ai_real.py with Groq API")
    print(f"  GROQ_API_KEY set: {'yes' if os.environ.get('GROQ_API_KEY') else 'NO - add it to .env'}")

    ctx = await test_extract_context()
    await test_embed_query(ctx)
    await test_embed_ad()
    await test_generate_response(ctx)
    await test_detect_engagement()

    print("\nAll contracts passed.\n")


if __name__ == "__main__":
    asyncio.run(main())
