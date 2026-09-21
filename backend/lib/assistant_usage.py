"""Additive usage ledger for the AI assistant (Phase 1).

Records an estimated token/cost snapshot per assistant call so usage is visible
before any budget/limit enforcement exists. Logging must never break the
assistant: `record_usage()` swallows its own errors — see its docstring.

Token counts are ESTIMATED, not exact. The OpenAI streaming call in
routers/assistant.py does not request `stream_options={"include_usage": True}`,
so no provider-reported usage is read from the response. The estimate uses a
simple chars/4 heuristic (a common rough ratio for English; Subly's Turkish text
tends to run slightly denser per token, so treat this as directional, not
billing-accurate). Swap `estimate_tokens` for a real tokenizer, or read the
real `usage` field once `include_usage` is requested, if exact accounting is
ever needed.
"""

import logging
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

UsageStatus = Literal["success", "error", "partial"]

CHARS_PER_TOKEN = 4  # rough heuristic; see module docstring

# USD per 1K tokens, keyed by "provider:model". Isolated here so a pricing update
# never touches router/business logic — edit this dict only.
PRICING_USD_PER_1K: dict[str, dict[str, float]] = {
    "openai:gpt-5.4": {"input": 0.005, "output": 0.015},
}
# Used for any provider/model pair not listed above, so a pricing gap logs a
# (clearly approximate) cost instead of crashing the request.
_DEFAULT_RATE = {"input": 0.005, "output": 0.015}


def estimate_tokens(text: str) -> int:
    """Rough token estimate from character count. See module docstring."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimated USD cost for one call. Unknown provider/model uses _DEFAULT_RATE."""
    rate = PRICING_USD_PER_1K.get(f"{provider}:{model}", _DEFAULT_RATE)
    cost = (input_tokens / 1000) * rate["input"] + (output_tokens / 1000) * rate["output"]
    return round(cost, 6)


def build_usage_record(
    *,
    user_id: str,
    provider: str,
    model: str,
    input_text: str,
    output_text: str,
    status: UsageStatus,
) -> dict:
    """Pure builder — no I/O, so it can be unit-tested without Mongo."""
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    return {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_total_tokens": input_tokens + output_tokens,
        "estimated_cost_usd": estimate_cost(provider, model, input_tokens, output_tokens),
        "status": status,
    }


async def record_usage(
    collection,
    *,
    user_id: str,
    provider: str,
    model: str,
    input_text: str,
    output_text: str,
    status: UsageStatus,
) -> None:
    """Insert one usage row into `collection` (normally `db.assistant_usage`).

    NEVER raises: a Mongo failure here must not break the assistant response the
    user is already streaming, so every error is logged and swallowed.
    """
    try:
        record = build_usage_record(
            user_id=user_id,
            provider=provider,
            model=model,
            input_text=input_text,
            output_text=output_text,
            status=status,
        )
        await collection.insert_one(record)
    except Exception:
        logger.exception("assistant usage logging failed (user_id=%s, status=%s)", user_id, status)
