"""Unit tests for the Phase 1 assistant usage ledger (lib/assistant_usage.py).

These test the module directly, with a fake Mongo collection standing in for
`db.assistant_usage` — no live server and no real Mongo needed. That is
deliberate: `record_usage()` takes an injectable collection object precisely so
this logic can be verified without the supervisor-managed backend + Mongo that
conftest.py's `client`/`aclient` fixtures require for endpoint tests.

asyncio_mode = auto (pytest.ini) — no @pytest.mark.asyncio needed on async tests.
"""

from lib.assistant_usage import (
    build_usage_record,
    estimate_cost,
    estimate_tokens,
    record_usage,
)


class _FakeCollection:
    """Minimal async stand-in for a Motor collection's insert_one()."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.inserted: list[dict] = []

    async def insert_one(self, doc: dict):
        if self.fail:
            raise RuntimeError("simulated Mongo failure")
        self.inserted.append(doc)


# ---------- token estimation ----------

def test_estimate_tokens_empty_string_is_zero():
    assert estimate_tokens("") == 0


def test_estimate_tokens_scales_with_length():
    short = estimate_tokens("abcd")
    long = estimate_tokens("abcd" * 100)
    assert short >= 1
    assert long > short


# ---------- cost calculation ----------

def test_estimate_cost_known_model_is_positive():
    cost = estimate_cost("openai", "gpt-5.4", input_tokens=1000, output_tokens=1000)
    assert cost > 0


def test_estimate_cost_unknown_model_falls_back_instead_of_raising():
    cost = estimate_cost("some-future-provider", "unlisted-model", input_tokens=500, output_tokens=500)
    assert cost >= 0


def test_estimate_cost_scales_with_token_count():
    small = estimate_cost("openai", "gpt-5.4", input_tokens=100, output_tokens=100)
    large = estimate_cost("openai", "gpt-5.4", input_tokens=10_000, output_tokens=10_000)
    assert large > small


# ---------- record builder (pure function) ----------

def test_build_usage_record_success_shape():
    record = build_usage_record(
        user_id="user_1", provider="openai", model="gpt-5.4",
        input_text="soru metni", output_text="cevap metni", status="success",
    )
    assert record["user_id"] == "user_1"
    assert record["provider"] == "openai"
    assert record["model"] == "gpt-5.4"
    assert record["status"] == "success"
    assert record["estimated_total_tokens"] == (
        record["estimated_input_tokens"] + record["estimated_output_tokens"]
    )
    assert record["estimated_cost_usd"] >= 0
    assert "created_at" in record


# ---------- record_usage() against a fake collection ----------

async def test_record_usage_success_inserts_one_document():
    coll = _FakeCollection()
    await record_usage(
        coll, user_id="user_1", provider="openai", model="gpt-5.4",
        input_text="soru", output_text="tam cevap", status="success",
    )
    assert len(coll.inserted) == 1
    assert coll.inserted[0]["status"] == "success"


async def test_record_usage_error_status_has_zero_output_tokens():
    coll = _FakeCollection()
    await record_usage(
        coll, user_id="user_1", provider="openai", model="gpt-5.4",
        input_text="soru", output_text="", status="error",
    )
    assert coll.inserted[0]["status"] == "error"
    assert coll.inserted[0]["estimated_output_tokens"] == 0


async def test_record_usage_partial_status_has_partial_output():
    coll = _FakeCollection()
    await record_usage(
        coll, user_id="user_1", provider="openai", model="gpt-5.4",
        input_text="soru", output_text="yarım cev", status="partial",
    )
    assert coll.inserted[0]["status"] == "partial"
    assert coll.inserted[0]["estimated_output_tokens"] >= 1


async def test_record_usage_logging_failure_does_not_raise():
    coll = _FakeCollection(fail=True)
    # Must not raise: routers/assistant.py awaits this after already streaming the
    # response to the user, so a Mongo failure here must never surface as a 500.
    await record_usage(
        coll, user_id="user_1", provider="openai", model="gpt-5.4",
        input_text="soru", output_text="cevap", status="success",
    )
    assert coll.inserted == []  # insert failed internally, but no exception escaped
