"""
Delete ads from the database.

Usage:
    # Delete all ads:
    python -m scripts.delete_ads

    # Delete ads for specific advertiser IDs:
    python -m scripts.delete_ads adv_nike adv_sony

    # Delete a specific ad by ad_id:
    python -m scripts.delete_ads --ad-id <uuid>
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.db import init_pools, close_pools, get_pg

SEED_ADVERTISER_IDS = [
    "adv_nike",
    "adv_sony",
    "adv_dyson",
    "adv_allbirds",
    "adv_notion",
]


async def main():
    args = sys.argv[1:]

    settings = get_settings()
    await init_pools(settings.database_dsn, settings.redis_url)
    pool = get_pg()

    async with pool.acquire() as conn:
        async with conn.transaction():
            if "--ad-id" in args:
                idx = args.index("--ad-id")
                ad_id = args[idx + 1]
                await conn.execute("DELETE FROM ad_context_history WHERE ad_id = $1::uuid", ad_id)
                await conn.execute("DELETE FROM events WHERE ad_id = $1::uuid", ad_id)
                result = await conn.execute("DELETE FROM ads WHERE ad_id = $1::uuid", ad_id)
                print(f"Deleted ad {ad_id}: {result}")

            elif args:
                advertiser_ids = args
                await conn.execute(
                    "DELETE FROM ad_context_history WHERE ad_id IN (SELECT ad_id FROM ads WHERE advertiser_id = ANY($1::text[]))",
                    advertiser_ids,
                )
                await conn.execute(
                    "DELETE FROM events WHERE ad_id IN (SELECT ad_id FROM ads WHERE advertiser_id = ANY($1::text[]))",
                    advertiser_ids,
                )
                result = await conn.execute(
                    "DELETE FROM ads WHERE advertiser_id = ANY($1::text[])",
                    advertiser_ids,
                )
                print(f"Deleted ads for {advertiser_ids}: {result}")

            else:
                await conn.execute(
                    "DELETE FROM ad_context_history WHERE ad_id IN (SELECT ad_id FROM ads WHERE advertiser_id = ANY($1::text[]))",
                    SEED_ADVERTISER_IDS,
                )
                await conn.execute(
                    "DELETE FROM events WHERE ad_id IN (SELECT ad_id FROM ads WHERE advertiser_id = ANY($1::text[]))",
                    SEED_ADVERTISER_IDS,
                )
                result = await conn.execute(
                    "DELETE FROM ads WHERE advertiser_id = ANY($1::text[])",
                    SEED_ADVERTISER_IDS,
                )
                print(f"Deleted all seed ads: {result}")

    await close_pools()


if __name__ == "__main__":
    asyncio.run(main())
