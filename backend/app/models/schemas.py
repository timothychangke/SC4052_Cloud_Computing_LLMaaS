"""
Shared data types that both the backend and the AI teammate's modules
agree on.  Keep this in sync with ad-llm-interface-contracts.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import date

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class AdReceptivity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class Intent(str, Enum):
    PRODUCT_RESEARCH = "product_research"
    COMPARISON = "comparison"
    PURCHASE = "purchase"
    GENERAL_QUESTION = "general_question"
    CASUAL_CHAT = "casual_chat"
    SUPPORT = "support"
    COMPLAINT = "complaint"
    SENSITIVE = "sensitive"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class AdvertiserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


# ── Core domain objects (dataclasses for internal use) ───────────────────

@dataclass
class Turn:
    role: str               # "user" or "assistant"
    content: str
    timestamp: str
    ad_id: Optional[str] = None  # set when an ad was shown in this turn


@dataclass
class ContextObject:
    intent: Intent
    topics: list[str]
    entities: list[str]
    sentiment: str           # "positive", "neutral", "negative", "mixed"
    purchase_signal: float   # 0.0 – 1.0
    ad_receptivity: AdReceptivity


@dataclass
class Ad:
    ad_id: str
    advertiser_id: str
    product_name: str
    product_description: str
    target_topics: list[str]
    target_intents: list[str]
    creative_text: str
    cta_url: str
    bid_cpm: float
    budget_remaining: float
    brand_safety_tags: list[str]
    similarity: Optional[float] = None   # filled after vector search
    score: Optional[float] = None        # filled after re-ranking


@dataclass
class ResponseObject:
    response_text: str
    ad_included: bool
    ad_id_used: Optional[str] = None


# ── Pydantic schemas for API request / response validation ──────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(..., min_length=1, max_length=128)


class AdMetadata(BaseModel):
    ad_id: str
    sponsored: bool


class ChatResponse(BaseModel):
    response: str
    ad_metadata: Optional[AdMetadata] = None


class AdCreatePayload(BaseModel):
    """Payload for bulk ad ingestion via the admin API."""
    advertiser_id: str
    product_name: str
    product_description: str = ""
    target_topics: list[str] = Field(default_factory=list)
    target_intents: list[str] = Field(default_factory=list)
    creative_text: str
    cta_url: str
    bid_cpm: float = Field(ge=0)
    budget_remaining: float = Field(ge=0)
    brand_safety_tags: list[str] = Field(default_factory=list)


class AdUpdatePayload(BaseModel):
    """Fields the admin can patch on an existing ad."""
    budget_remaining: Optional[float] = None
    active: Optional[bool] = None
    creative_text: Optional[str] = None
    bid_cpm: Optional[float] = None


class AnalyticsSummary(BaseModel):
    impressions: int
    clicks: int
    engagements: int
    ctr: float
    estimated_revenue: float
    top_ads: list[dict]


# ── Advertiser Portal schemas ────────────────────────────────────────────

# -- Advertiser --

class AdvertiserCreatePayload(BaseModel):
    advertiser_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=500)
    contact_email: Optional[str] = None
    company_name: Optional[str] = None
    billing_email: Optional[str] = None


class AdvertiserUpdatePayload(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    company_name: Optional[str] = None
    billing_email: Optional[str] = None
    status: Optional[AdvertiserStatus] = None


class AdvertiserResponse(BaseModel):
    advertiser_id: str
    name: str
    contact_email: Optional[str] = None
    company_name: Optional[str] = None
    billing_email: Optional[str] = None
    status: str
    created_at: str


# -- Campaign --

class CampaignCreatePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    total_budget: float = Field(gt=0)
    daily_budget: Optional[float] = Field(default=None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignUpdatePayload(BaseModel):
    name: Optional[str] = None
    total_budget: Optional[float] = Field(default=None, gt=0)
    daily_budget: Optional[float] = Field(default=None, ge=0)  # 0 = remove cap
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignResponse(BaseModel):
    campaign_id: str
    advertiser_id: str
    name: str
    status: str
    total_budget: float
    daily_budget: Optional[float]
    total_spent: float
    today_spent: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: str
    updated_at: str


# -- Campaign Ad (create ad within a campaign) --

class CampaignAdCreatePayload(BaseModel):
    product_name: str = Field(..., min_length=1)
    product_description: str = ""
    target_topics: list[str] = Field(default_factory=list)
    target_intents: list[str] = Field(default_factory=list)
    creative_text: str
    cta_url: str
    bid_cpm: float = Field(ge=0)
    budget_remaining: float = Field(ge=0)
    brand_safety_tags: list[str] = Field(default_factory=list)


# -- Portal Analytics --

class CampaignAnalyticsResponse(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    total_budget: float
    total_spent: float
    impressions: int
    clicks: int
    engagements: int
    ctr: float
    daily_breakdown: list[dict]


class AdvertiserAnalyticsResponse(BaseModel):
    advertiser_id: str
    name: str
    total_campaigns: int
    active_campaigns: int
    total_spent: float
    total_budget: float
    impressions: int
    clicks: int
    engagements: int
    ctr: float
    campaigns: list[dict]