"""
Adaptive ad context optimizer.

Reviews engagement metrics for an ad, asks the LLM to diagnose
what's working and what isn't, and generates an improved context.md
that gets injected into future response synthesis prompts.
"""

from __future__ import annotations

import json

import structlog

from app.core.db import get_pg

log = structlog.get_logger()

MIN_ENGAGEMENTS = 5          # don't optimize with too little data
MIN_HOURS_BETWEEN = 24       # minimum hours between optimizations


async def optimize_ad_context(ad_id: str, lookback_days: int = 7) -> str | None:
    """
    Review engagement metrics for an ad and generate an improved context.md.
    Returns the new context text, or None if optimization was skipped.
    """
    pool = get_pg()

    ad_row = await pool.fetchrow(
        """SELECT ad_id::text, product_name, product_description, creative_text,
                  target_topics, target_intents, ad_context, ad_context_version,
                  ad_context_updated_at
           FROM ads WHERE ad_id = $1::uuid""",
        ad_id,
    )
    if not ad_row:
        log.warning("context_optimizer.ad_not_found", ad_id=ad_id)
        return None

    if ad_row["ad_context_updated_at"]:
        from datetime import datetime, timezone, timedelta
        hours_since = (
            datetime.now(timezone.utc) - ad_row["ad_context_updated_at"].replace(tzinfo=timezone.utc)
        ).total_seconds() / 3600
        if hours_since < MIN_HOURS_BETWEEN:
            log.info("context_optimizer.too_soon", ad_id=ad_id, hours_since=round(hours_since, 1))
            return None

    current_context = ad_row["ad_context"] or "(no context yet)"

    metrics = await pool.fetchrow("""
        SELECT
            COUNT(*) as total_engagements,
            AVG((payload->>'engagement_score')::float) as avg_engagement_score,
            AVG((payload->>'ad_naturalness_score')::float) as avg_naturalness,
            AVG((payload->>'purchase_proximity')::float) as avg_purchase_proximity,
            COUNT(*) FILTER (WHERE payload->>'sentiment_toward_ad' = 'positive') as positive_count,
            COUNT(*) FILTER (WHERE payload->>'sentiment_toward_ad' = 'negative') as negative_count,
            COUNT(*) FILTER (WHERE payload->>'engagement_type' = 'dismissal') as dismissals,
            COUNT(*) FILTER (WHERE payload->>'engagement_type' = 'purchase_intent') as purchase_intents,
            COUNT(*) FILTER (WHERE payload->>'engagement_type' = 'negative_reaction') as negative_reactions
        FROM events
        WHERE ad_id = $1::uuid
          AND event_type = 'engagement'
          AND created_at > NOW() - ($2 || ' days')::interval
    """, ad_id, str(lookback_days))

    if (metrics["total_engagements"] or 0) < MIN_ENGAGEMENTS:
        log.info("context_optimizer.insufficient_data", ad_id=ad_id,
                 engagements=metrics["total_engagements"])
        return None

    impressions = await pool.fetchval("""
        SELECT COUNT(*) FROM events
        WHERE ad_id = $1::uuid AND event_type = 'impression'
          AND created_at > NOW() - ($2 || ' days')::interval
    """, ad_id, str(lookback_days))

    recent_feedback = await pool.fetch("""
        SELECT payload->>'reasoning' as reasoning,
               payload->>'engagement_type' as eng_type,
               payload->>'sentiment_toward_ad' as sentiment
        FROM events
        WHERE ad_id = $1::uuid AND event_type = 'engagement'
          AND created_at > NOW() - ($2 || ' days')::interval
        ORDER BY created_at DESC
        LIMIT 10
    """, ad_id, str(lookback_days))

    feedback_text = "\n".join(
        f"- [{r['eng_type']}, {r['sentiment']}]: {r['reasoning']}"
        for r in recent_feedback
    ) or "(no engagement data yet)"

    eng_rate = (metrics["total_engagements"] / max(impressions, 1)) * 100
    avg_score = metrics["avg_engagement_score"] or 0
    avg_nat = metrics["avg_naturalness"] or 0
    avg_purch = metrics["avg_purchase_proximity"] or 0

    prompt = f"""You are an advertising optimization strategist for a conversational AI platform.

An AI assistant recommends products naturally within chat conversations. Each ad has a
"context guide" that instructs the assistant on HOW to present the product (tone, angle,
emphasis, what to avoid). Your job is to improve this context guide based on real
engagement data.

IMPORTANT: The context guide must NEVER instruct the assistant to hide the sponsored
nature of the recommendation. [Sponsored] disclosure is mandatory and non-negotiable.

## Current Ad
- Product: {ad_row['product_name']}
- Description: {ad_row['product_description']}
- Creative: {ad_row['creative_text']}
- Target Topics: {', '.join(ad_row['target_topics'] or [])}

## Current Context Guide
{current_context}

## Performance Metrics (last {lookback_days} days)
- Impressions: {impressions}
- Total engagements: {metrics['total_engagements']}
- Engagement rate: {eng_rate:.1f}%
- Avg engagement score: {avg_score:.2f}/1.0
- Avg naturalness score: {avg_nat:.2f}/1.0
- Avg purchase proximity: {avg_purch:.2f}/1.0
- Positive sentiment: {metrics['positive_count']}, Negative: {metrics['negative_count']}
- Dismissals: {metrics['dismissals']}, Purchase intents: {metrics['purchase_intents']}

## Recent Engagement Samples
{feedback_text}

## Your Task
Based on the metrics above, write an IMPROVED context guide. Specifically:
- If naturalness is low (< 0.6), adjust tone guidance to make integration feel more organic.
- If engagement score is low (< 0.4), suggest more compelling angles or better-matched situations.
- If negative sentiment is high, identify what's turning users off and add "avoid" guidance.
- If purchase proximity is high but conversion is low, add urgency/CTA guidance.
- If dismissals are high, reconsider when/how this ad should be presented.

Return ONLY the improved context guide as plain text bullet points.
Then on a new line, write "---REASONING---" followed by a brief explanation of what you changed and why."""

    from app.core.config import get_settings

    if get_settings().ai_module_mode == "real":
        from app.services.ai_real import _get_groq, _CHAT_MODEL
        resp = await _get_groq().chat.completions.create(
            model=_CHAT_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        output = resp.choices[0].message.content.strip()
    else:
        output = (
            f"• Lead with {ad_row['product_name']}'s strongest differentiator when the user is actively researching\n"
            f"• Use a casual, peer-recommendation tone — 'you might like' rather than 'you should buy'\n"
            f"• Mention one specific feature that matches the user's stated need\n"
            f"• Avoid price comparisons or urgency language — let the product speak for itself\n"
            f"• Only mention when the conversation is clearly about this product category\n"
            f"---REASONING---\n"
            f"Mock optimization: adjusted tone guidance for naturalness and added specificity to feature mentions."
        )

    if "---REASONING---" in output:
        new_context, reasoning = output.split("---REASONING---", 1)
        new_context = new_context.strip()
        reasoning = reasoning.strip()
    else:
        new_context = output
        reasoning = ""

    new_version = (ad_row["ad_context_version"] or 0) + 1

    await pool.execute("""
        UPDATE ads
        SET ad_context = $1,
            ad_context_version = $2,
            ad_context_updated_at = NOW()
        WHERE ad_id = $3::uuid
    """, new_context, new_version, ad_id)

    metrics_snapshot = {
        "impressions": impressions,
        "total_engagements": metrics["total_engagements"],
        "avg_engagement_score": float(avg_score),
        "avg_naturalness": float(avg_nat),
        "avg_purchase_proximity": float(avg_purch),
        "positive_count": metrics["positive_count"],
        "negative_count": metrics["negative_count"],
        "engagement_rate": round(eng_rate, 2),
    }

    await pool.execute("""
        INSERT INTO ad_context_history
            (ad_id, version, context_text, optimization_reasoning, metrics_snapshot)
        VALUES ($1::uuid, $2, $3, $4, $5)
    """, ad_id, new_version, new_context, reasoning, json.dumps(metrics_snapshot))

    log.info("context_optimizer.done", ad_id=ad_id, version=new_version)
    return new_context