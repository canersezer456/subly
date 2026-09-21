"""Router-level tests for the Phase 2 budget gate in routers/assistant.py.

These call `chat()` directly as a plain async function — bypassing FastAPI's
HTTP layer, dependency injection wiring, and any live server — with two fakes
swapped in for this module only:
  - a fake `db` (in-memory collections), so no real Mongo is touched.
  - a fake `emergentintegrations.llm.chat` module injected into sys.modules
    (only for the "under budget" test), so no network call or private
    package install is needed.

The "over budget" test deliberately does NOT install the fake
emergentintegrations module. That is the actual proof the LLM is never
called on that path: if routers/assistant.py's budget gate ever regressed to
importing emergentintegrations before checking the budget, this test would
fail with ModuleNotFoundError, since the real (private) package is not
installed in this environment.
"""

import json

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


def _install_fake_emergentintegrations(monkeypatch, reply_text: str = "test cevabı"):
    import sys
    import types

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


async def test_assistant_denies_and_skips_llm_call_when_over_budget(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(assistant_module, "db", fake_db)
    monkeypatch.setattr(assistant_module, "check_budget", _fake_check_budget(allowed=False, usage=999, limit=100))
    # emergentintegrations is deliberately NOT faked/installed here — see module docstring.

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert any("error" in f for f in frames)
    assert frames[-1] == {"done": True}
    assert fake_db.assistant_messages.inserted == []  # no user/assistant message written
    assert fake_db.assistant_usage.inserted == []  # Phase 1 logging not invoked on the denied path


async def test_assistant_calls_llm_and_records_usage_when_under_budget(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(assistant_module, "db", fake_db)
    monkeypatch.setattr(assistant_module, "check_budget", _fake_check_budget(allowed=True, usage=10, limit=1000))
    monkeypatch.setattr(assistant_module, "_build_context", _fake_build_context)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "test-key")
    _install_fake_emergentintegrations(monkeypatch, reply_text="test cevabı")

    response = await assistant_module.chat(ChatRequest(message="merhaba"), user={"user_id": "user_1"})
    frames = await _consume_sse(response)

    assert {"delta": "test cevabı"} in frames
    assert frames[-1] == {"done": True}
    assert len(fake_db.assistant_messages.inserted) == 2  # user turn + assistant reply
    assert len(fake_db.assistant_usage.inserted) == 1  # Phase 1 usage ledger still recorded
    assert fake_db.assistant_usage.inserted[0]["status"] == "success"
