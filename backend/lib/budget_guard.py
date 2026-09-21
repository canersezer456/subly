"""Minimal per-user daily AI usage budget on top of the Phase 1 usage ledger (Phase 2).

Deliberately small scope: one env var, one pure decision function, one usage
lookup against `db.assistant_usage` (see lib/assistant_usage.py). No plan/tier
system, no per-provider/per-model limits, no circuit breaker, no caching — a
single global daily token cap is all Phase 2 adds.
"""

import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# A rough day's worth of assistant conversation. Deliberately generous for an
# MVP with no billing yet — tune via ASSISTANT_DAILY_TOKEN_BUDGET once real
# usage data from the Phase 1 ledger shows what typical users consume.
DEFAULT_DAILY_TOKEN_BUDGET = 50_000

# Matches lib.dates.today_iso's own default so "today" means the same day
# across the app (finance.py anchors it to Europe/Istanbul via APP_TZ too).
_DEFAULT_TZ = "UTC"


def get_daily_token_budget() -> int:
    """Reads ASSISTANT_DAILY_TOKEN_BUDGET; falls back to the default when the
    variable is missing, not an integer, or not positive. Never raises.
    """
    raw = os.environ.get("ASSISTANT_DAILY_TOKEN_BUDGET")
    if raw is None:
        return DEFAULT_DAILY_TOKEN_BUDGET
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.error(
            "ASSISTANT_DAILY_TOKEN_BUDGET=%r is not an integer; using default %d",
            raw, DEFAULT_DAILY_TOKEN_BUDGET,
        )
        return DEFAULT_DAILY_TOKEN_BUDGET
    if value <= 0:
        logger.error(
            "ASSISTANT_DAILY_TOKEN_BUDGET=%r must be positive; using default %d",
            raw, DEFAULT_DAILY_TOKEN_BUDGET,
        )
        return DEFAULT_DAILY_TOKEN_BUDGET
    return value


def _today_utc_bounds(tz: str | None = None) -> tuple[str, str]:
    """ISO-8601 UTC-offset [start, end) bounds for "today" in `tz`.

    `assistant_usage.created_at` is always `datetime.now(timezone.utc).isoformat()`
    (Phase 1), so comparing against UTC-offset bounds here — rather than
    truncating to a date string — stays correct for any `tz`.
    """
    zone = ZoneInfo(tz or os.environ.get("APP_TZ", _DEFAULT_TZ))
    local_date = datetime.now(zone).date()
    start_local = datetime(local_date.year, local_date.month, local_date.day, tzinfo=zone)
    end_local = start_local + timedelta(days=1)
    return start_local.isoformat(), end_local.isoformat()


async def get_daily_usage_tokens(collection, *, user_id: str, tz: str | None = None) -> int:
    """Sums estimated_total_tokens recorded for `user_id` since the start of today.

    Fails safe: any lookup error is logged and treated as zero usage, so a
    Mongo hiccup degrades to "budget check permits the request" rather than
    blocking the assistant outright — see evaluate_budget's docstring for why
    that is the correct failure direction here.
    """
    try:
        start, end = _today_utc_bounds(tz)
        cursor = collection.find(
            {"user_id": user_id, "created_at": {"$gte": start, "$lt": end}},
            {"estimated_total_tokens": 1, "_id": 0},
        )
        total = 0
        async for doc in cursor:
            total += doc.get("estimated_total_tokens", 0)
        return total
    except Exception:
        logger.exception("daily usage lookup failed (user_id=%s); treating as zero usage", user_id)
        return 0


def evaluate_budget(*, daily_usage_tokens: int, daily_limit_tokens: int) -> dict:
    """Pure allow/deny decision — no I/O, so it is trivially unit-testable.

    Denies once usage has already reached the limit (usage >= limit): this
    check runs BEFORE the next call is made, so "exactly at budget" must deny
    that next call, or the user would end up strictly over budget after it.
    """
    allowed = daily_usage_tokens < daily_limit_tokens
    return {
        "allowed": allowed,
        "daily_usage_tokens": daily_usage_tokens,
        "daily_limit_tokens": daily_limit_tokens,
        "reason": "under daily budget" if allowed else "daily assistant token budget reached",
    }


async def check_budget(collection, *, user_id: str, tz: str | None = None) -> dict:
    """Look up today's usage, then evaluate it.

    Composed entirely from get_daily_token_budget() and get_daily_usage_tokens(),
    both of which already never raise (see their docstrings), so this cannot
    raise either — callers do not need an extra try/except around it.
    """
    limit = get_daily_token_budget()
    usage = await get_daily_usage_tokens(collection, user_id=user_id, tz=tz)
    return evaluate_budget(daily_usage_tokens=usage, daily_limit_tokens=limit)
