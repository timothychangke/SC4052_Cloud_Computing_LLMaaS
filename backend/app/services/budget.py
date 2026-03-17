"""
Budget management & daily pacing logic.

check_budget()  — called during ad retrieval to gate campaign eligibility
record_spend()  — called after each impression to track campaign-level spend
"""

from __future__ import annotations

import structlog

from app.core.db import get_pg

log = structlog.get_logger()


async def _maybe_reset_daily_spend(campaign_id: str):
    """
    Lazy daily reset: if today_date on the campaign row is in the past,
    zero out today_spent and update today_date.  This avoids needing a
    cron job — the reset happens on the first touch each new day.
    """
    pool = get_pg()
    result = await pool.execute(
        """
        UPDATE campaigns
        SET today_spent = 0,
            today_date = CURRENT_DATE
        WHERE campaign_id = $1::uuid
          AND today_date < CURRENT_DATE
        """,
        campaign_id,
    )
    if result and result != "UPDATE 0":
        log.info("budget.daily_reset", campaign_id=campaign_id)


async def check_budget(campaign_id: str) -> bool:
    """
    Returns True if the campaign is eligible to serve ads right now.
    Returns False if any budget/schedule constraint is violated.
    """
    pool = get_pg()

    await _maybe_reset_daily_spend(campaign_id)

    row = await pool.fetchrow(
        """
        SELECT status, total_budget, total_spent,
               daily_budget, today_spent,
               start_date, end_date
        FROM campaigns
        WHERE campaign_id = $1::uuid
        """,
        campaign_id,
    )

    if row is None:
        log.warning("budget.campaign_not_found", campaign_id=campaign_id)
        return False

    if row["status"] != "active":
        return False

    if row["total_spent"] >= row["total_budget"]:
        return False

    if row["daily_budget"] is not None and row["today_spent"] >= row["daily_budget"]:
        return False

    if row["start_date"] is not None:
        from datetime import date
        if row["start_date"] > date.today():
            return False

    if row["end_date"] is not None:
        from datetime import date
        if row["end_date"] < date.today():
            return False

    return True


async def record_spend(campaign_id: str, amount: float):
    """
    Increment total_spent and today_spent on the campaign, upsert into
    daily_spend_log, and auto-complete the campaign if budget is exhausted.
    """
    pool = get_pg()

    # reset daily counter if date rolled over
    await _maybe_reset_daily_spend(campaign_id)

    # increment campaign-level spend
    await pool.execute(
        """
        UPDATE campaigns
        SET total_spent = total_spent + $1,
            today_spent = today_spent + $1,
            updated_at = NOW()
        WHERE campaign_id = $2::uuid
        """,
        amount,
        campaign_id,
    )

    # upsert daily_spend_log
    await pool.execute(
        """
        INSERT INTO daily_spend_log (campaign_id, spend_date, impressions, spend)
        VALUES ($1::uuid, CURRENT_DATE, 1, $2)
        ON CONFLICT (campaign_id, spend_date)
        DO UPDATE SET
            impressions = daily_spend_log.impressions + 1,
            spend = daily_spend_log.spend + $2
        """,
        campaign_id,
        amount,
    )

    # auto-complete campaign if total budget exhausted
    await pool.execute(
        """
        UPDATE campaigns
        SET status = 'completed'
        WHERE campaign_id = $1::uuid
          AND total_spent >= total_budget
          AND status = 'active'
        """,
        campaign_id,
    )

    log.info("budget.spend_recorded", campaign_id=campaign_id, amount=amount)