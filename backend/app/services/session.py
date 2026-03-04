"""
Session manager: owns every read/write to Redis for conversation state.

Key schema:  session:{session_id}  →  JSON blob
TTL:         30 min of inactivity (configurable)

The session keeps a rolling window of the last N turns so we don't
blow up the LLM's context window, plus accumulated topics and the
list of ads already shown (for frequency capping).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.core.db import get_redis
from app.core.config import get_settings
from app.models.schemas import Turn

log = structlog.get_logger()


def _key(session_id: str) -> str:
    return f"session:{session_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_session(session_id: str) -> dict:
    """
    Fetch the session blob from Redis.  Returns a sensible default
    if the session doesn't exist yet (first message).
    """
    raw = await get_redis().get(_key(session_id))
    if raw is None:
        return {
            "turns": [],
            "accumulated_topics": [],
            "purchase_signals_history": [],
            "ads_shown_this_session": [],
            "turn_count": 0,
            "created_at": _now_iso(),
            "last_active": _now_iso(),
        }
    return json.loads(raw)


async def save_session(session_id: str, session: dict):
    """Persist session back to Redis with a fresh TTL."""
    settings = get_settings()
    session["last_active"] = _now_iso()
    await get_redis().set(
        _key(session_id),
        json.dumps(session),
        ex=settings.session_ttl_seconds,
    )


async def append_turn(session_id: str, role: str, content: str, ad_id: Optional[str] = None):
    """
    Add a turn to the session and trim to the rolling window.
    Also bumps turn_count.
    """
    settings = get_settings()
    session = await get_session(session_id)

    turn = {
        "role": role,
        "content": content,
        "timestamp": _now_iso(),
        "ad_id": ad_id,
    }
    session["turns"].append(turn)

    # keep only the last N turns so the LLM prompt stays manageable
    max_turns = settings.max_history_turns
    if len(session["turns"]) > max_turns:
        session["turns"] = session["turns"][-max_turns:]

    session["turn_count"] += 1
    await save_session(session_id, session)
    return session


async def record_ad_shown(session_id: str, ad_id: str):
    """Track that we showed this ad so we don't repeat it (frequency cap)."""
    session = await get_session(session_id)
    if ad_id not in session["ads_shown_this_session"]:
        session["ads_shown_this_session"].append(ad_id)
    await save_session(session_id, session)


async def update_topics_and_signals(
    session_id: str,
    topics: list[str],
    purchase_signal: float,
):
    """
    Accumulate topics across the session (deduped) and keep a running
    list of purchase signals so we can eyeball trends later.
    """
    session = await get_session(session_id)

    existing = set(session["accumulated_topics"])
    for t in topics:
        existing.add(t)
    session["accumulated_topics"] = list(existing)

    session["purchase_signals_history"].append(round(purchase_signal, 3))

    await save_session(session_id, session)


def session_turns_to_domain(session: dict) -> list[Turn]:
    """Convert the raw dicts stored in Redis into Turn dataclasses."""
    return [
        Turn(
            role=t["role"],
            content=t["content"],
            timestamp=t["timestamp"],
            ad_id=t.get("ad_id"),
        )
        for t in session.get("turns", [])
    ]
