"""
Basic health check.  Hit this to make sure the service is up
and can talk to Postgres + Redis.
"""

from fastapi import APIRouter

from app.core.db import get_pg, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    # quick sanity checks — if either of these fails the service is unhealthy
    pg_ok = False
    redis_ok = False

    try:
        await get_pg().fetchval("SELECT 1")
        pg_ok = True
    except Exception:
        pass

    try:
        await get_redis().ping()
        redis_ok = True
    except Exception:
        pass

    status = "ok" if (pg_ok and redis_ok) else "degraded"
    return {"status": status, "postgres": pg_ok, "redis": redis_ok}
