"""
Seed fake engagement events with the new rich metrics payload.
Run with: python -m scripts.seed_engagements
"""

import asyncio
import json
import random
from datetime import datetime, timezone, timedelta

from app.core.config import get_settings
from app.core.db import init_pools, get_pg

ENGAGEMENT_TYPES = [
    "product_inquiry", "comparison", "price_inquiry",
    "purchase_intent", "feature_question", "positive_reaction",
    "negative_reaction", "dismissal", "none",
]

SENTIMENTS = ["positive", "neutral", "negative"]


def random_payload():
    eng_type = random.choice(ENGAGEMENT_TYPES[:6])  # bias toward positive types
    sentiment = random.choices(SENTIMENTS, weights=[5, 3, 1])[0]
    return json.dumps({
        "follow_up_message": "Tell me more about that product",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engagement_type": eng_type,
        "engagement_score": round(random.uniform(0.3, 0.95), 3),
        "sentiment_toward_ad": sentiment,
        "ad_naturalness_score": round(random.uniform(0.4, 0.9), 3),
        "purchase_proximity": round(random.uniform(0.1, 0.8), 3),
        "follow_up_topic_match": random.choice([True, True, True, False]),
        "reasoning": f"Mock: user showed {eng_type} with {sentiment} sentiment",
    })


async def main():
    settings = get_settings()
    await init_pools(settings.database_dsn, settings.redis_url)
    pool = get_pg()

    # Get all active ad IDs
    rows = await pool.fetch("SELECT ad_id::text FROM ads WHERE active = true LIMIT 10")
    if not rows:
        print("No active ads found. Run your ad seeding script first.")
        return

    count = 0
    for row in rows:
        ad_id = row["ad_id"]

        # Create 8-15 engagement events per ad
        n = random.randint(8, 15)
        for i in range(n):
            ts = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
            )
            await pool.execute(
                """
                INSERT INTO events (event_type, session_id, ad_id, payload, created_at)
                VALUES ($1, $2, $3::uuid, $4, $5)
                """,
                "engagement",
                f"test_session_{random.randint(1000, 9999)}",
                ad_id,
                random_payload(),
                ts,
            )
            count += 1

        # Also seed some impressions so engagement rate works
        for i in range(random.randint(30, 80)):
            ts = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
            )
            await pool.execute(
                """
                INSERT INTO events (event_type, session_id, ad_id, payload, created_at)
                VALUES ($1, $2, $3::uuid, $4, $5)
                """,
                "impression",
                f"test_session_{random.randint(1000, 9999)}",
                ad_id,
                json.dumps({"turn_number": 1, "timestamp": ts.isoformat()}),
                ts,
            )

    print(f"Seeded {count} engagement events + impressions for {len(rows)} ads.")


if __name__ == "__main__":
    asyncio.run(main())