"""Router-level tests for the Phase 2 budget gate in routers/assistant.py.

These call `chat()` directly as a plain async function — bypassing FastAPI's
HTTP layer, dependency injection wiring, and any live server — with fakes
swapped in for this module only:
  - a fake `db` (in-memory collections), so no real Mongo is touched.
  - a fake `AsyncOpenAI` (the official OpenAI SDK client used by
    routers/assistant.py), so no real network call or API key is needed.

The "over budget" test uses a poison-pill fake for `AsyncOpenAI` that raises
if ever constructed — that is the actual proof the LLM is never reached on
that path, since a real `AsyncOpenAI()` call would otherwise happen silently.
"""

import json
import types

import routers.assistant as assistant_module
from models.finance import ChatRequest


class _FakeCursor:
    """Fake Motor cursor: supports the same .sort().to_list() chain
    routers/assistant.py's existing (pre-Phase-2) code already uses on
    db.assistant_messages.find(...).
    """

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
    """Same shape as test_assistant_usage.py's fake, plus a find() supporting
    Motor's cursor chaining so the pre-existing history lookup in chat() keeps
    working against it.
    """

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


def _fake_check_budget(*, allowed: bool, usage: int = 0, limit: int = 1000):
    async def _check(collection, *, user_id, tz=None):
        return {
            "allowed": allowed,
            "daily_usage_tokens": usage,
            "daily_limit_tokens": limit,
            "reason": "test",
        }

    return _check


async def _fake_build_context(user_id: str) -> str:
    # Sidesteps lib/finance.py's real Mongo-backed summary pipeline — Phase 2
    # only needs to verify the budget gate + LLM call + Phase 1 logging, not
    # re-prove _build_context's own (pre-existing) correctness.
    return "{}"


class _AsyncOpenAINeverCalled:
    """Poison pill: fails loudly if the budget-denied path ever tries to
    construct a real OpenAI client — the actual proof the LLM is never
    reached, not just an assumption.
    """

    def __init__(self, *args, **kwargs):
        raise AssertionError("AsyncOpenAI must not be constructed when the budget gate denies a request")


def _install_fake_openai(monkeypatch, *, reply_text: str = "test cevabı"):
    class _FakeStream:
        def __aiter__(self):
            return self._gen()

        async def _gen(self):
            yield types.SimpleNamespace(
                choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content=reply_text))]
            )

    class _FakeCompletions:
        async def create(self, **kwargs):
            return _FakeStream()

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = _FakeChat()

    monkeypatch.setattr(assistant_module, "AsyncOpenAI", _FakeAsyncOpenAI)


async def _consume_sse(response) -> list[dict]:
    frames = []
    async for chunk in response.body_iterator:
        text = chunk if isinstance(chunk, str) else chunk.decode()
        for line in text.splitlines():
            if line.startswith("data: "):
                frames.append(json.loads(line[len("data: "):]))
    return frames


async def test_assistant_denies_and_skips_llm_call_when_over_budget(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(assistant_module, "db", fake_db)
    monkeypatch.setattr(assistant_module, "check_budget", _fake_check_budget(allowed=False, usage=999, limit=100))
    monkeypatch.setattr(assistant_module, "AsyncOpenAI", _AsyncOpenAINeverCalled)

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert any("error" in f for f in frames)
    assert any(f.get("code") == "budget_exceeded" for f in frames)  # Phase 4: structured error code
    assert frames[-1] == {"done": True}
    assert fake_db.assistant_messages.inserted == []  # no user/assistant message written
    assert fake_db.assistant_usage.inserted == []  # Phase 1 logging not invoked on the denied path


async def test_assistant_calls_llm_and_records_usage_when_under_budget(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(assistant_module, "db", fake_db)
    monkeypatch.setattr(assistant_module, "check_budget", _fake_check_budget(allowed=True, usage=10, limit=1000))
    monkeypatch.setattr(assistant_module, "_build_context", _fake_build_context)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _install_fake_openai(monkeypatch, reply_text="test cevabı")

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert {"delta": "test cevabı"} in frames
    assert frames[-1] == {"done": True}
    assert len(fake_db.assistant_messages.inserted) == 2  # user turn + assistant reply
    assert len(fake_db.assistant_usage.inserted) == 1  # Phase 1 usage ledger still recorded
    assert fake_db.assistant_usage.inserted[0]["status"] == "success"
