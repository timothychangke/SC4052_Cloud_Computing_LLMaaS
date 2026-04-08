"""
Seed script — populates the ads table with some test data so you
don't have to stare at empty query results during development.

Usage:
    python -m scripts.seed_ads

It calls the AI module's embed_ad() (or the mock) to generate
embeddings, so make sure the app can import properly.
"""

import asyncio
import sys
import os

# make sure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.db import init_pools, close_pools, get_pg
from app.services.ai import embed_ad


SAMPLE_ADS = [
    {
        "advertiser_id": "adv_nike",
        "product_name": "Nike Pegasus 41",
        "product_description": "Lightweight daily trainer with responsive ZoomX foam. Great for neutral runners doing easy to moderate miles.",
        "target_topics": ["running shoes", "marathon", "jogging", "fitness"],
        "target_intents": ["product_research", "comparison", "purchase"],
        "creative_text": "The Nike Pegasus 41 offers responsive ZoomX foam for your daily runs.",
        "cta_url": "https://nike.com/pegasus-41?utm_source=adllm",
        "bid_cpm": 12.50,
        "budget_remaining": 5000.00,
        "brand_safety_tags": ["sports", "fitness", "health"],
        "product_image_url": "https://static.nike.com/a/images/t_web_pdp_535_v2/f_auto,u_9ddf04c7-2a9a-4d76-add1-d15af8f0263d,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/63c4596a-ca9a-4a56-82f3-0387903ed5f1/AIR+ZOOM+PEGASUS+41.png",
    },
    {
        "advertiser_id": "adv_sony",
        "product_name": "Sony WH-1000XM5",
        "product_description": "Industry-leading noise cancelling headphones with 30-hour battery life and crystal-clear call quality.",
        "target_topics": ["headphones", "noise cancelling", "audio", "music", "work from home"],
        "target_intents": ["product_research", "comparison", "purchase"],
        "creative_text": "Experience silence with Sony WH-1000XM5 noise cancelling headphones.",
        "cta_url": "https://sony.com/wh1000xm5?utm_source=adllm",
        "bid_cpm": 15.00,
        "budget_remaining": 8000.00,
        "brand_safety_tags": ["electronics", "audio", "technology"],
        "product_image_url": "https://cdn.shopify.com/s/files/1/0397/7166/8635/products/WH1000XM5_Black.png?v=1761235815",
    },
    {
        "advertiser_id": "adv_dyson",
        "product_name": "Dyson V15 Detect",
        "product_description": "Cordless vacuum with laser dust detection and HEPA filtration. Shows particle counts on an LCD screen.",
        "target_topics": ["vacuum", "cleaning", "home appliances", "smart home"],
        "target_intents": ["product_research", "comparison", "purchase"],
        "creative_text": "See what you've been missing with the Dyson V15 Detect laser vacuum.",
        "cta_url": "https://dyson.com/v15-detect?utm_source=adllm",
        "bid_cpm": 18.00,
        "budget_remaining": 6000.00,
        "brand_safety_tags": ["home", "appliances", "technology"],
        "product_image_url": "https://dyson-h.assetsadobe2.com/is/image/content/dam/dyson/products/vacuum-cleaners-category/dyson-v12-vacuum/shop-all-v15/V15%20-%20Shop%20all%20hero%20module_HEPA_LB-V15-US.jpg?$responsive$&cropPathE=desktop&fit=stretch,1&wid=3840",
    },
    {
        "advertiser_id": "adv_allbirds",
        "product_name": "Allbirds Tree Runners",
        "product_description": "Sustainable everyday sneakers made from eucalyptus tree fiber. Lightweight, breathable, and machine washable.",
        "target_topics": ["sneakers", "sustainable fashion", "shoes", "casual shoes"],
        "target_intents": ["product_research", "comparison", "purchase"],
        "creative_text": "Walk lighter on the planet with Allbirds Tree Runners.",
        "cta_url": "https://allbirds.com/tree-runners?utm_source=adllm",
        "bid_cpm": 10.00,
        "budget_remaining": 3000.00,
        "brand_safety_tags": ["fashion", "sustainability", "lifestyle"],
    },
    {
        "advertiser_id": "adv_notion",
        "product_name": "Notion Team Plan",
        "product_description": "All-in-one workspace for notes, docs, wikis, and project management. Collaborative editing with AI-powered features.",
        "target_topics": ["productivity", "project management", "note taking", "team collaboration", "software"],
        "target_intents": ["product_research", "comparison"],
        "creative_text": "Organize your team's work in one place with Notion.",
        "cta_url": "https://notion.so/teams?utm_source=adllm",
        "bid_cpm": 20.00,
        "budget_remaining": 10000.00,
        "brand_safety_tags": ["software", "productivity", "business"],
    },
]


async def main():
    settings = get_settings()
    await init_pools(settings.database_dsn, settings.redis_url)

    pool = get_pg()

    # run schema first (in case this is a fresh db)
    from app.main import SCHEMA_SQL
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)

    print(f"Seeding {len(SAMPLE_ADS)} ads...")

    for ad in SAMPLE_ADS:
        embedding = await embed_ad(
            ad["product_name"],
            ad["product_description"],
            ad["target_topics"],
            ad["target_intents"],
        )
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        await pool.execute(
            """
            INSERT INTO ads (
                advertiser_id, product_name, product_description,
                target_topics, target_intents, creative_text, cta_url,
                bid_cpm, budget_remaining, brand_safety_tags, embedding,
                product_image_url
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::vector,$12)
            """,
            ad["advertiser_id"],
            ad["product_name"],
            ad["product_description"],
            ad["target_topics"],
            ad["target_intents"],
            ad["creative_text"],
            ad["cta_url"],
            ad["bid_cpm"],
            ad["budget_remaining"],
            ad["brand_safety_tags"],
            embedding_str,
            ad.get("product_image_url"),
        )
        print(f"  ✓ {ad['product_name']}")

    print("Done! Ads seeded successfully.")
    await close_pools()


if __name__ == "__main__":
    asyncio.run(main())