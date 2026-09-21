"""Unit tests for the Phase 2 daily budget guard (lib/budget_guard.py).

Same approach as test_assistant_usage.py: a fake in-memory Mongo-like
collection stands in for `db.assistant_usage`, so these run without a live
server or real Mongo.
"""

from datetime import datetime, timedelta, timezone

from lib.budget_guard import (
    DEFAULT_DAILY_TOKEN_BUDGET,
    check_budget,
    evaluate_budget,
    get_daily_token_budget,
    get_daily_usage_tokens,
)


class _FakeUsageCollection:
    """Minimal async stand-in for Motor's find() over assistant_usage documents.

    Supports exactly the query shape budget_guard.py uses: an exact match on
    `user_id` and a `$gte`/`$lt` range on `created_at` (both ISO-8601 strings,
    which compare correctly lexicographically for a fixed UTC offset — the
    same assumption the production code relies on).
    """

    def __init__(self, docs):
        self.docs = docs

    def find(self, query, projection=None):
        user_id = query.get("user_id")
        created_at_filter = query.get("created_at", {})
        gte = created_at_filter.get("$gte")
        lt = created_at_filter.get("$lt")

        def matches(doc):
            if user_id is not None and doc.get("user_id") != user_id:
                return False
            created_at = doc.get("created_at")
            if gte is not None and created_at < gte:
                return False
            if lt is not None and created_at >= lt:
                return False
            return True

        matched = [doc for doc in self.docs if matches(doc)]

        async def _cursor():
            for doc in matched:
                yield doc

        return _cursor()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ---------- evaluate_budget (pure) ----------

def test_evaluate_budget_under_limit_is_allowed():
    result = evaluate_budget(daily_usage_tokens=100, daily_limit_tokens=1000)
    assert result["allowed"] is True


def test_evaluate_budget_exactly_at_limit_is_denied():
    # At the limit, one more call would push usage strictly over it — deny.
    # See evaluate_budget's docstring for why this is the chosen direction.
    result = evaluate_budget(daily_usage_tokens=1000, daily_limit_tokens=1000)
    assert result["allowed"] is False


def test_evaluate_budget_over_limit_is_denied():
    result = evaluate_budget(daily_usage_tokens=1500, daily_limit_tokens=1000)
    assert result["allowed"] is False


def test_evaluate_budget_zero_usage_is_allowed():
    result = evaluate_budget(daily_usage_tokens=0, daily_limit_tokens=1000)
    assert result["allowed"] is True


# ---------- get_daily_token_budget (env configuration) ----------

def test_get_daily_token_budget_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("ASSISTANT_DAILY_TOKEN_BUDGET", raising=False)
    assert get_daily_token_budget() == DEFAULT_DAILY_TOKEN_BUDGET


def test_get_daily_token_budget_reads_env_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_DAILY_TOKEN_BUDGET", "12345")
    assert get_daily_token_budget() == 12345


def test_get_daily_token_budget_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_DAILY_TOKEN_BUDGET", "not-a-number")
    assert get_daily_token_budget() == DEFAULT_DAILY_TOKEN_BUDGET


def test_get_daily_token_budget_falls_back_on_non_positive_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_DAILY_TOKEN_BUDGET", "0")
    assert get_daily_token_budget() == DEFAULT_DAILY_TOKEN_BUDGET


# ---------- get_daily_usage_tokens (today's usage calculation) ----------

async def test_get_daily_usage_tokens_sums_only_todays_records_for_that_user():
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1, hours=1)
    docs = [
        {"user_id": "user_1", "created_at": _iso(now), "estimated_total_tokens": 100},
        {"user_id": "user_1", "created_at": _iso(now), "estimated_total_tokens": 50},
        {"user_id": "user_1", "created_at": _iso(yesterday), "estimated_total_tokens": 999},  # excluded: not today
        {"user_id": "user_2", "created_at": _iso(now), "estimated_total_tokens": 999},  # excluded: different user
    ]
    coll = _FakeUsageCollection(docs)
    total = await get_daily_usage_tokens(coll, user_id="user_1")
    assert total == 150


async def test_get_daily_usage_tokens_returns_zero_with_no_records():
    coll = _FakeUsageCollection([])
    total = await get_daily_usage_tokens(coll, user_id="user_1")
    assert total == 0


async def test_get_daily_usage_tokens_fails_open_on_lookup_error():
    class _BrokenCollection:
        def find(self, *args, **kwargs):
            raise RuntimeError("simulated Mongo failure")

    total = await get_daily_usage_tokens(_BrokenCollection(), user_id="user_1")
    assert total == 0


# ---------- check_budget (composition) ----------

async def test_check_budget_allows_under_limit(monkeypatch):
    monkeypatch.setenv("ASSISTANT_DAILY_TOKEN_BUDGET", "1000")
    now = datetime.now(timezone.utc)
    coll = _FakeUsageCollection([{"user_id": "user_1", "created_at": _iso(now), "estimated_total_tokens": 100}])
    result = await check_budget(coll, user_id="user_1")
    assert result["allowed"] is True
    assert result["daily_usage_tokens"] == 100
    assert result["daily_limit_tokens"] == 1000


async def test_check_budget_denies_over_limit(monkeypatch):
    monkeypatch.setenv("ASSISTANT_DAILY_TOKEN_BUDGET", "100")
    now = datetime.now(timezone.utc)
    coll = _FakeUsageCollection([{"user_id": "user_1", "created_at": _iso(now), "estimated_total_tokens": 150}])
    result = await check_budget(coll, user_id="user_1")
    assert result["allowed"] is False
