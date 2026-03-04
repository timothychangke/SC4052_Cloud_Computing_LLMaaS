"""
Connection pools for Postgres (asyncpg) and Redis.
Created once at startup and torn down on shutdown via FastAPI lifespan.
"""

from __future__ import annotations

import asyncpg
import redis.asyncio as aioredis
import structlog

log = structlog.get_logger()

# module-level refs that get populated in init_pools()
_pg_pool: asyncpg.Pool | None = None
_redis: aioredis.Redis | None = None


async def init_pools(database_dsn: str, redis_url: str):
    """Call once at startup."""
    global _pg_pool, _redis

    log.info("db.connecting", dsn=database_dsn.split("@")[-1])  # don't log creds
    _pg_pool = await asyncpg.create_pool(dsn=database_dsn, min_size=2, max_size=10)

    log.info("redis.connecting", url=redis_url)
    _redis = aioredis.from_url(redis_url, decode_responses=True)
    await _redis.ping()

    log.info("pools.ready")


async def close_pools():
    global _pg_pool, _redis
    if _pg_pool:
        await _pg_pool.close()
    if _redis:
        await _redis.aclose()
    log.info("pools.closed")


def get_pg() -> asyncpg.Pool:
    assert _pg_pool is not None, "Postgres pool not initialised — did startup run?"
    return _pg_pool


def get_redis() -> aioredis.Redis:
    assert _redis is not None, "Redis client not initialised — did startup run?"
    return _redis
