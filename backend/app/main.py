"""
Ad LLM Orchestrator — FastAPI application entry point.

Startup:
  - Connects to Postgres + Redis
  - Runs schema migration (creates tables if they don't exist)
Shutdown:
  - Closes connection pools cleanly

All the real logic lives in the routers and services.  This file
is just plumbing.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import init_pools, close_pools, get_pg
from app.core.logging import setup_logging
from app.routers import chat, track, admin, analytics, health

setup_logging(json_output=False)  # flip to True in prod
log = structlog.get_logger()


# ── DB schema bootstrap ─────────────────────────────────────────────────
# We run this on every startup so you don't have to remember to run
# migrations separately.  It's idempotent (CREATE IF NOT EXISTS).

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ads (
    ad_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advertiser_id VARCHAR(255) NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    product_description TEXT,
    target_topics TEXT[],
    target_intents TEXT[],
    creative_text TEXT NOT NULL,
    cta_url VARCHAR(2048) NOT NULL,
    bid_cpm DECIMAL(10,2) NOT NULL,
    budget_remaining DECIMAL(10,2) NOT NULL,
    brand_safety_tags TEXT[],
    embedding vector(768),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    ad_id UUID REFERENCES ads(ad_id),
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS advertisers (
    advertiser_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    contact_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes (IF NOT EXISTS isn't supported for all index types in older PG,
-- but the DO block handles the "already exists" case gracefully)
DO $$
BEGIN
    -- vector similarity index — ivfflat needs rows to exist, but the
    -- CREATE is fine on an empty table; it just won't be useful until
    -- you've inserted some ads.
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'ads_embedding_idx'
    ) THEN
        CREATE INDEX ads_embedding_idx ON ads
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_type'
    ) THEN
        CREATE INDEX idx_events_type ON events(event_type);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_ad_id'
    ) THEN
        CREATE INDEX idx_events_ad_id ON events(ad_id);
    END IF;

    IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_created'
        ) THEN
            CREATE INDEX idx_events_created ON events(created_at);
        END IF;
    END$$;

    -- ── Advertiser table expansions ─────────────────────────────────────────
    ALTER TABLE advertisers ADD COLUMN IF NOT EXISTS company_name VARCHAR(500);
    ALTER TABLE advertisers ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255);
    ALTER TABLE advertisers ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';

    -- ── Campaigns table ─────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS campaigns (
        campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        advertiser_id VARCHAR(255) NOT NULL REFERENCES advertisers(advertiser_id),
        name VARCHAR(500) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'draft',
        total_budget DECIMAL(12,2) NOT NULL,
        daily_budget DECIMAL(12,2),
        total_spent DECIMAL(12,2) NOT NULL DEFAULT 0,
        today_spent DECIMAL(12,2) NOT NULL DEFAULT 0,
        today_date DATE NOT NULL DEFAULT CURRENT_DATE,
        start_date DATE,
        end_date DATE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_campaigns_advertiser'
        ) THEN
            CREATE INDEX idx_campaigns_advertiser ON campaigns(advertiser_id);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_campaigns_status'
        ) THEN
            CREATE INDEX idx_campaigns_status ON campaigns(status);
        END IF;
    END$$;

    -- ── Link ads to campaigns ───────────────────────────────────────────────
    ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES campaigns(campaign_id);

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_ads_campaign'
        ) THEN
            CREATE INDEX idx_ads_campaign ON ads(campaign_id);
        END IF;
    END$$;

    -- ── Daily spend log ─────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS daily_spend_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id),
        spend_date DATE NOT NULL,
        impressions INT NOT NULL DEFAULT 0,
        clicks INT NOT NULL DEFAULT 0,
        engagements INT NOT NULL DEFAULT 0,
        spend DECIMAL(12,2) NOT NULL DEFAULT 0,
        UNIQUE(campaign_id, spend_date)
    );

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_daily_spend_campaign'
        ) THEN
            CREATE INDEX idx_daily_spend_campaign ON daily_spend_log(campaign_id, spend_date);
        END IF;
    END$$;
    """

async def _run_migrations():
    pool = get_pg()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    log.info("db.schema_ready")


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_pools(settings.database_dsn, settings.redis_url)
    await _run_migrations()
    log.info("app.started", mode=settings.ai_module_mode)
    yield
    await close_pools()
    log.info("app.shutdown")


# ── App factory ──────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Ad LLM Orchestrator",
        description="Conversational ad platform backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — let the React frontend talk to us
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # mount all routers
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(track.router)
    app.include_router(admin.router)
    app.include_router(analytics.router)

    return app


app = create_app()
