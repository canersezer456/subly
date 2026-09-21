"""Minimal circuit breaker around the AI assistant provider call (Phase 3).

Guards ONLY provider/LLM failures. Auth failures, budget denials, invalid
input, and DB logging failures never reach this module and never affect its
state — see routers/assistant.py's integration order (budget gate runs first
and is untouched by circuit state) and record_failure()'s docstring.

Single global breaker for the whole process: Subly's assistant has exactly
one provider integration point (the official OpenAI SDK -> gpt-5.4), so one
breaker instance is enough — no per-user/per-provider registry, no Redis,
no external coordination. Lazy recovery (checked on the next call), not a
background timer, to keep this small.
"""

import asyncio
import logging
import os
import time

logger = logging.getLogger(__name__)

CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"

DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_COOLDOWN_SECONDS = 60.0


def _get_failure_threshold() -> int:
    """Reads ASSISTANT_CIRCUIT_FAILURE_THRESHOLD; falls back to the default
    when missing, not an integer, or not positive. Never raises.
    """
    raw = os.environ.get("ASSISTANT_CIRCUIT_FAILURE_THRESHOLD")
    if raw is None:
        return DEFAULT_FAILURE_THRESHOLD
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.error(
            "ASSISTANT_CIRCUIT_FAILURE_THRESHOLD=%r is not an integer; using default %d",
            raw, DEFAULT_FAILURE_THRESHOLD,
        )
        return DEFAULT_FAILURE_THRESHOLD
    if value <= 0:
        logger.error(
            "ASSISTANT_CIRCUIT_FAILURE_THRESHOLD=%r must be positive; using default %d",
            raw, DEFAULT_FAILURE_THRESHOLD,
        )
        return DEFAULT_FAILURE_THRESHOLD
    return value


def _get_cooldown_seconds() -> float:
    """Reads ASSISTANT_CIRCUIT_COOLDOWN_SECONDS; falls back to the default
    when missing, not a number, or not positive. Never raises.
    """
    raw = os.environ.get("ASSISTANT_CIRCUIT_COOLDOWN_SECONDS")
    if raw is None:
        return DEFAULT_COOLDOWN_SECONDS
    try:
        value = float(raw)
    except (TypeError, ValueError):
        logger.error(
            "ASSISTANT_CIRCUIT_COOLDOWN_SECONDS=%r is not a number; using default %s",
            raw, DEFAULT_COOLDOWN_SECONDS,
        )
        return DEFAULT_COOLDOWN_SECONDS
    if value <= 0:
        logger.error(
            "ASSISTANT_CIRCUIT_COOLDOWN_SECONDS=%r must be positive; using default %s",
            raw, DEFAULT_COOLDOWN_SECONDS,
        )
        return DEFAULT_COOLDOWN_SECONDS
    return value


class CircuitBreaker:
    """Small, process-local, asyncio-safe 3-state breaker.

    `failure_threshold` / `cooldown_seconds` / `clock` are constructor
    overrides for tests (deterministic thresholds, no real sleeping); the
    router uses the module-level singleton (`get_circuit_breaker()`), which
    reads live env vars via the two functions above.

    Concurrency: every state read/mutation happens under one asyncio.Lock, so
    concurrent requests in the same process cannot corrupt state or both slip
    through as "the" HALF_OPEN probe (`_half_open_probe_in_flight` claims that
    single slot). This is sufficient for the current single-process FastAPI
    deployment; it is not a distributed circuit breaker.
    """

    def __init__(self, *, failure_threshold: int | None = None, cooldown_seconds: float | None = None, clock=time.monotonic):
        self._failure_threshold_override = failure_threshold
        self._cooldown_seconds_override = cooldown_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._state = CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_probe_in_flight = False

    def _threshold(self) -> int:
        return self._failure_threshold_override if self._failure_threshold_override is not None else _get_failure_threshold()

    def _cooldown(self) -> float:
        return self._cooldown_seconds_override if self._cooldown_seconds_override is not None else _get_cooldown_seconds()

    @property
    def state(self) -> str:
        return self._state

    async def allow_request(self) -> bool:
        """True if a provider call may proceed right now.

        Performs the lazy OPEN -> HALF_OPEN transition once the cooldown has
        elapsed, and — if so — claims the single HALF_OPEN probe slot in the
        same locked step, so two requests racing at the cooldown boundary
        cannot both be told "go".
        """
        async with self._lock:
            if self._state == CLOSED:
                return True
            if self._state == OPEN:
                elapsed = self._clock() - self._opened_at if self._opened_at is not None else 0
                if elapsed >= self._cooldown():
                    self._state = HALF_OPEN
                    self._half_open_probe_in_flight = True
                    return True
                return False
            # HALF_OPEN
            if self._half_open_probe_in_flight:
                return False
            self._half_open_probe_in_flight = True
            return True

    async def record_success(self) -> None:
        """Call after a provider call actually succeeds. Closes the circuit
        and clears the failure count, whatever state it was in.
        """
        async with self._lock:
            self._state = CLOSED
            self._failure_count = 0
            self._opened_at = None
            self._half_open_probe_in_flight = False

    async def record_failure(self) -> None:
        """Call after a provider call actually fails.

        Callers must only invoke this for genuine provider/LLM failures — the
        try/except around `llm.stream_message(...)` in routers/assistant.py
        is exactly that boundary. It must never be called for auth failures,
        budget denials, invalid input, or DB logging failures, since none of
        those reach that boundary.
        """
        async with self._lock:
            if self._state == HALF_OPEN:
                # The one probe failed: reopen and restart the cooldown clock.
                self._state = OPEN
                self._opened_at = self._clock()
                self._half_open_probe_in_flight = False
                return
            self._failure_count += 1
            if self._failure_count >= self._threshold():
                self._state = OPEN
                self._opened_at = self._clock()


_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """The single process-wide breaker instance routers/assistant.py uses."""
    return _breaker
