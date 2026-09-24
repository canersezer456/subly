"""Real FastAPI/auth routes backed exclusively by the test-only database."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from isolated_store import create_app
from lib.db import db
from lib import finance


@pytest.fixture
def clients():
    for collection in db.collections.values():
        collection.docs.clear()
    app = create_app()
    with TestClient(app, base_url="https://testserver") as a, TestClient(app, base_url="https://testserver") as b:
        for client, name in ((a, "alpha"), (b, "beta")):
            r = client.post("/api/auth/register", json={"email": f"{name}@example.com", "name": name, "password": "TestPass123!"})
            assert r.status_code == 200
        yield a, b


def subscription(name):
    return {"name": name, "category": "Eğlence", "price": 20, "currency": "USD", "renewal_date": finance.today().isoformat(), "billing_cycle": "monthly"}


def test_ab_empty_owned_and_foreign_mutations(clients):
    a, b = clients
    for client in clients:
        assert client.get("/api/subscriptions").json() == []
        assert client.get("/api/dashboard/summary").json()["upcoming"] == []
    ar = a.post("/api/subscriptions", json=subscription("Netflix")).json()
    assert b.get("/api/subscriptions").json() == []
    br = b.post("/api/subscriptions", json=subscription("Spotify")).json()
    for client, other, own, foreign in ((a, b, ar, br), (b, a, br, ar)):
        assert [s["name"] for s in client.get("/api/subscriptions").json()] == [own["name"]]
        assert client.patch(f'/api/subscriptions/{foreign["id"]}', json={"price": 1}).status_code == 404
        assert client.delete(f'/api/subscriptions/{foreign["id"]}').status_code == 404
        for path in ("dashboard/summary", "calendar", "alerts", "account/export"):
            response = client.get(f"/api/{path}")
            assert response.status_code == 200
            assert foreign["name"] not in response.text
        assert other.get("/api/subscriptions").json()[0]["price"] == 20


def test_normal_user_cannot_scan_fabricated_subscriptions(clients):
    response = clients[0].post("/api/subscriptions/mock-scan")
    assert response.status_code in (403, 409, 501)
    assert clients[0].get("/api/subscriptions").json() == []


def test_invalid_new_date_rejected(clients):
    response = clients[0].post("/api/subscriptions", json={**subscription("Netflix"), "renewal_date": "2026-02-31"})
    assert response.status_code == 422


def test_month_end_anchor_does_not_drift():
    assert finance.next_occurrence(date(2026, 1, 31), "monthly", date(2026, 3, 1)) == date(2026, 3, 31)
    assert finance.next_occurrence(date(2024, 2, 29), "yearly", date(2028, 1, 1)) == date(2028, 2, 29)


def test_only_active_subscriptions_are_upcoming():
    data = {"bills": [], "subscriptions": [dict(subscription("Netflix"), id=str(i), status=status) for i, status in enumerate(("active", "cancelled", "expired", "paused"))]}
    assert [p["id"] for p in finance.upcoming_payments(data, finance.today())] == ["0"]


def test_paid_future_bill_not_upcoming():
    data = {"subscriptions": [], "bills": [{"id": "bill", "provider": "Power", "amount": 10, "bill_type": "Utilities", "status": "paid", "frequency": "once", "due_date": (finance.today() + timedelta(days=1)).isoformat()}]}
    assert finance.upcoming_payments(data, finance.today()) == []
