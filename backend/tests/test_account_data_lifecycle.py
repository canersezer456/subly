"""Tests for the Phase 4 account data-lifecycle fix: assistant_usage now
participates in account export/delete, the same way assistant_messages
already did.

Two things are verified independently, because they can fail independently:
  1. USER_COLLECTIONS actually includes "assistant_usage" (routers/account.py).
  2. The AccountExport Pydantic model actually declares an `assistant_usage`
     field (models/finance.py) — FastAPI's `response_model=AccountExport`
     silently drops any key not declared on the model, so (1) alone would
     look done while the real HTTP export endpoint kept discarding the data.

`export_account`/`delete_account` are called directly as plain async
functions (same technique as the assistant router tests) — no live server,
no real Mongo, no HTTP layer, using a small fake db supporting both
`db["name"]` and `db.name` access (routers/account.py uses the former,
`delete_account`'s user_sessions/users cleanup uses the latter).
"""

from fastapi import Response

import routers.account as account_module
from models.finance import AccountExport


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    async def to_list(self, length=None):
        return self._docs[:length] if length is not None else list(self._docs)


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.deleted_many_filters: list[dict] = []
        self.deleted_one_filters: list[dict] = []

    def find(self, query=None, projection=None):
        return _FakeCursor(self.docs)

    async def delete_many(self, query):
        self.deleted_many_filters.append(query)

    async def delete_one(self, query):
        self.deleted_one_filters.append(query)


class _FakeDb:
    """Supports both db["name"] (routers/account.py's USER_COLLECTIONS loop)
    and db.name (delete_account's user_sessions/users cleanup).
    """

    def __init__(self, seed: dict | None = None):
        self._collections: dict[str, _FakeCollection] = {}
        for name, docs in (seed or {}).items():
            self._collections[name] = _FakeCollection(docs)

    def _get(self, name: str) -> _FakeCollection:
        if name not in self._collections:
            self._collections[name] = _FakeCollection()
        return self._collections[name]

    def __getitem__(self, name: str) -> _FakeCollection:
        return self._get(name)

    def __getattr__(self, name: str) -> _FakeCollection:
        return self._get(name)


def test_user_collections_includes_assistant_usage():
    assert "assistant_usage" in account_module.USER_COLLECTIONS


def test_account_export_model_declares_assistant_usage_field():
    # The actual bug this guards against: USER_COLLECTIONS alone does not
    # guarantee the field survives response_model serialization.
    export = AccountExport(
        exported_at="2026-01-01T00:00:00+00:00",
        user={"user_id": "user_1"},
        incomes=[], expenses=[], bills=[], budgets=[], subscriptions=[],
        assistant_messages=[],
        assistant_usage=[{"id": "u1", "estimated_total_tokens": 42}],
        digest_prefs=[],
    )
    assert export.assistant_usage == [{"id": "u1", "estimated_total_tokens": 42}]


async def test_export_account_includes_assistant_usage_rows(monkeypatch):
    fake_db = _FakeDb({"assistant_usage": [{"id": "u1", "user_id": "user_1", "estimated_total_tokens": 42}]})
    monkeypatch.setattr(account_module, "db", fake_db)

    payload = await account_module.export_account(user={"user_id": "user_1", "email": "a@b.com"})

    assert payload["assistant_usage"] == [{"id": "u1", "user_id": "user_1", "estimated_total_tokens": 42}]


async def test_delete_account_deletes_assistant_usage_rows(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(account_module, "db", fake_db)

    await account_module.delete_account(request=None, response=Response(), user={"user_id": "user_1"})

    assert {"user_id": "user_1"} in fake_db._get("assistant_usage").deleted_many_filters
