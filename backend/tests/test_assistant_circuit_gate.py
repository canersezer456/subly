"""Router-level tests for the Phase 3 circuit breaker in routers/assistant.py.

Same approach as test_assistant_budget_gate.py: `chat()` is called directly as
a plain async function, with fakes swapped in for `db`, `check_budget`,
`get_circuit_breaker`, and (where needed) `emergentintegrations.llm.chat` —
no live server, no real Mongo, no network, no real sleeping.

Each test uses its own fresh CircuitBreaker instance (never the module-level
singleton) so tests cannot leak state into each other.
"""

import json
import sys
import types

import routers.assistant as assistant_module
from lib.circuit_breaker import CLOSED, OPEN, CircuitBreaker
from models.finance import ChatRequest


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction=1):
        self._docs = sorted(self._docs, key=lambda d: d.get(field), reverse=direction < 0)
        return self

    async def to_list(self, length=None):
        return self._docs[:length] if length is not None else list(self._docs)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for doc in self._docs:
            yield doc


class _FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []
        self.inserted: list[dict] = []

    async def insert_one(self, doc: dict):
        self.docs.append(doc)
        self.inserted.append(doc)

    def find(self, query=None, projection=None):
        return _FakeCursor(self.docs)


class _FakeDb:
    def __init__(self):
        self.assistant_messages = _FakeCollection()
        self.assistant_usage = _FakeCollection()


def _fake_check_budget(*, allowed: bool):
    async def _check(collection, *, user_id, tz=None):
        return {"allowed": allowed, "daily_usage_tokens": 0, "daily_limit_tokens": 1000, "reason": "test"}

    return _check


async def _fake_build_context(user_id: str) -> str:
    return "{}"


def _install_fake_emergentintegrations(monkeypatch, *, reply_text: str = "test cevabı", should_fail: bool = False):
    class UserMessage:
        def __init__(self, text: str):
            self.text = text

    class TextDelta:
        def __init__(self, content: str):
            self.content = content

    class StreamDone:
        pass

    class LlmChat:
        def __init__(self, **kwargs):
            pass

        def with_model(self, provider, model):
            return self

        async def stream_message(self, message):
            if should_fail:
                raise RuntimeError("simulated provider failure")
            yield TextDelta(content=reply_text)
            yield StreamDone()

    chat_module = types.ModuleType("emergentintegrations.llm.chat")
    chat_module.LlmChat = LlmChat
    chat_module.StreamDone = StreamDone
    chat_module.TextDelta = TextDelta
    chat_module.UserMessage = UserMessage

    llm_module = types.ModuleType("emergentintegrations.llm")
    llm_module.chat = chat_module

    root_module = types.ModuleType("emergentintegrations")
    root_module.llm = llm_module

    monkeypatch.setitem(sys.modules, "emergentintegrations", root_module)
    monkeypatch.setitem(sys.modules, "emergentintegrations.llm", llm_module)
    monkeypatch.setitem(sys.modules, "emergentintegrations.llm.chat", chat_module)


async def _consume_sse(response) -> list[dict]:
    frames = []
    async for chunk in response.body_iterator:
        text = chunk if isinstance(chunk, str) else chunk.decode()
        for line in text.splitlines():
            if line.startswith("data: "):
                frames.append(json.loads(line[len("data: "):]))
    return frames


def _setup(monkeypatch, *, budget_allowed: bool, breaker: CircuitBreaker) -> _FakeDb:
    fake_db = _FakeDb()
    monkeypatch.setattr(assistant_module, "db", fake_db)
    monkeypatch.setattr(assistant_module, "check_budget", _fake_check_budget(allowed=budget_allowed))
    monkeypatch.setattr(assistant_module, "_build_context", _fake_build_context)
    monkeypatch.setattr(assistant_module, "get_circuit_breaker", lambda: breaker)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "test-key")
    return fake_db


async def test_budget_denied_never_touches_circuit_state(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=100.0)
    _setup(monkeypatch, budget_allowed=False, breaker=breaker)
    # emergentintegrations deliberately NOT installed — a budget denial must
    # return before the breaker gate (and therefore long before the LLM
    # import), so this would fail with ModuleNotFoundError if that ordering
    # regressed.

    await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})

    assert breaker.state == CLOSED  # untouched: still its initial state


async def test_circuit_open_skips_llm_call(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=100.0)
    await breaker.record_failure()  # threshold=1 -> already OPEN
    assert breaker.state == OPEN
    fake_db = _setup(monkeypatch, budget_allowed=True, breaker=breaker)
    # emergentintegrations deliberately NOT installed — proves the LLM is
    # genuinely never called while the circuit is open.

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert any("error" in f for f in frames)
    assert frames[-1] == {"done": True}
    assert fake_db.assistant_messages.inserted == []
    assert fake_db.assistant_usage.inserted == []  # no LLM call -> nothing to log


async def test_circuit_closed_calls_llm(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=100.0)
    _setup(monkeypatch, budget_allowed=True, breaker=breaker)
    _install_fake_emergentintegrations(monkeypatch, reply_text="test cevabı")

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert {"delta": "test cevabı"} in frames
    assert frames[-1] == {"done": True}
    assert breaker.state == CLOSED


async def test_provider_failure_trips_circuit(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=100.0)
    _setup(monkeypatch, budget_allowed=True, breaker=breaker)
    _install_fake_emergentintegrations(monkeypatch, should_fail=True)

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    await _consume_sse(response)

    assert breaker.state == OPEN


async def test_successful_provider_call_resets_failure_count(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=100.0)
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.state == CLOSED  # below threshold still
    _setup(monkeypatch, budget_allowed=True, breaker=breaker)
    _install_fake_emergentintegrations(monkeypatch, reply_text="ok")

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    await _consume_sse(response)

    assert breaker.state == CLOSED
    # The success must have reset the failure count, not just left it below
    # threshold: two more failures alone should NOT reach threshold=3.
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.state == CLOSED


async def test_existing_phase2_behavior_intact_when_budget_denied(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=100.0)
    fake_db = _setup(monkeypatch, budget_allowed=False, breaker=breaker)

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert any("error" in f for f in frames)
    assert frames[-1] == {"done": True}
    assert fake_db.assistant_messages.inserted == []
    assert fake_db.assistant_usage.inserted == []


async def test_phase1_usage_logging_intact_on_successful_call(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=100.0)
    fake_db = _setup(monkeypatch, budget_allowed=True, breaker=breaker)
    _install_fake_emergentintegrations(monkeypatch, reply_text="test cevabı")

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    await _consume_sse(response)

    assert len(fake_db.assistant_usage.inserted) == 1
    assert fake_db.assistant_usage.inserted[0]["status"] == "success"


async def test_phase1_usage_logging_records_error_on_provider_failure(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=100.0)
    fake_db = _setup(monkeypatch, budget_allowed=True, breaker=breaker)
    _install_fake_emergentintegrations(monkeypatch, should_fail=True)

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    await _consume_sse(response)

    assert len(fake_db.assistant_usage.inserted) == 1
    assert fake_db.assistant_usage.inserted[0]["status"] == "error"
