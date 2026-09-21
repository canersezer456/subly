"""Unit tests for the Phase 3 circuit breaker (lib/circuit_breaker.py).

A fake, manually-advanced clock replaces time.monotonic so cooldown behavior
is deterministic and instant — no real sleeping.
"""

import asyncio

from lib.circuit_breaker import (
    CLOSED,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_FAILURE_THRESHOLD,
    HALF_OPEN,
    OPEN,
    CircuitBreaker,
    _get_cooldown_seconds,
    _get_failure_threshold,
)


class _FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _breaker(*, threshold=3, cooldown=10.0, clock=None):
    return CircuitBreaker(failure_threshold=threshold, cooldown_seconds=cooldown, clock=clock or _FakeClock())


# ---------- state machine ----------

async def test_initial_state_is_closed():
    breaker = _breaker()
    assert breaker.state == CLOSED
    assert await breaker.allow_request() is True


async def test_failures_below_threshold_remain_closed():
    breaker = _breaker(threshold=3)
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.state == CLOSED
    assert await breaker.allow_request() is True


async def test_threshold_failure_opens_circuit():
    breaker = _breaker(threshold=3)
    await breaker.record_failure()
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.state == OPEN


async def test_open_rejects_calls():
    breaker = _breaker(threshold=1, cooldown=100.0)
    await breaker.record_failure()
    assert breaker.state == OPEN
    assert await breaker.allow_request() is False


async def test_open_transitions_to_half_open_after_cooldown():
    clock = _FakeClock()
    breaker = _breaker(threshold=1, cooldown=10.0, clock=clock)
    await breaker.record_failure()
    assert breaker.state == OPEN

    clock.advance(5)
    assert await breaker.allow_request() is False  # cooldown not elapsed yet
    assert breaker.state == OPEN

    clock.advance(10)
    assert await breaker.allow_request() is True  # elapsed -> probe granted
    assert breaker.state == HALF_OPEN


async def test_half_open_allows_exactly_one_attempt():
    clock = _FakeClock()
    breaker = _breaker(threshold=1, cooldown=10.0, clock=clock)
    await breaker.record_failure()
    clock.advance(11)

    assert await breaker.allow_request() is True   # the one probe
    assert await breaker.allow_request() is False  # a second caller is refused
    assert breaker.state == HALF_OPEN


async def test_successful_half_open_attempt_closes_and_resets():
    clock = _FakeClock()
    breaker = _breaker(threshold=1, cooldown=10.0, clock=clock)
    await breaker.record_failure()
    clock.advance(11)
    assert await breaker.allow_request() is True

    await breaker.record_success()

    assert breaker.state == CLOSED
    assert await breaker.allow_request() is True  # fully usable again


async def test_failed_half_open_attempt_reopens_and_restarts_cooldown():
    clock = _FakeClock()
    breaker = _breaker(threshold=1, cooldown=10.0, clock=clock)
    await breaker.record_failure()
    clock.advance(11)
    assert await breaker.allow_request() is True

    await breaker.record_failure()

    assert breaker.state == OPEN
    assert await breaker.allow_request() is False  # new cooldown, not elapsed yet
    clock.advance(11)
    assert await breaker.allow_request() is True   # new cooldown elapsed -> HALF_OPEN again


# ---------- env configuration ----------

def test_failure_threshold_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("ASSISTANT_CIRCUIT_FAILURE_THRESHOLD", raising=False)
    assert _get_failure_threshold() == DEFAULT_FAILURE_THRESHOLD


def test_failure_threshold_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_CIRCUIT_FAILURE_THRESHOLD", "not-a-number")
    assert _get_failure_threshold() == DEFAULT_FAILURE_THRESHOLD


def test_failure_threshold_falls_back_on_non_positive_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_CIRCUIT_FAILURE_THRESHOLD", "0")
    assert _get_failure_threshold() == DEFAULT_FAILURE_THRESHOLD


def test_failure_threshold_reads_env_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_CIRCUIT_FAILURE_THRESHOLD", "9")
    assert _get_failure_threshold() == 9


def test_cooldown_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("ASSISTANT_CIRCUIT_COOLDOWN_SECONDS", raising=False)
    assert _get_cooldown_seconds() == DEFAULT_COOLDOWN_SECONDS


def test_cooldown_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_CIRCUIT_COOLDOWN_SECONDS", "soon")
    assert _get_cooldown_seconds() == DEFAULT_COOLDOWN_SECONDS


def test_cooldown_falls_back_on_non_positive_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_CIRCUIT_COOLDOWN_SECONDS", "-5")
    assert _get_cooldown_seconds() == DEFAULT_COOLDOWN_SECONDS


def test_cooldown_reads_env_value(monkeypatch):
    monkeypatch.setenv("ASSISTANT_CIRCUIT_COOLDOWN_SECONDS", "30")
    assert _get_cooldown_seconds() == 30.0


# ---------- concurrency ----------

async def test_concurrent_half_open_probes_grant_exactly_one():
    clock = _FakeClock()
    breaker = _breaker(threshold=1, cooldown=10.0, clock=clock)
    await breaker.record_failure()
    clock.advance(11)

    results = await asyncio.gather(*(breaker.allow_request() for _ in range(20)))

    assert results.count(True) == 1
    assert results.count(False) == 19


async def test_concurrent_failures_do_not_corrupt_the_count():
    breaker = _breaker(threshold=10)
    await asyncio.gather(*(breaker.record_failure() for _ in range(10)))
    # If the counter lost updates to a race, this would still be CLOSED.
    assert breaker.state == OPEN
