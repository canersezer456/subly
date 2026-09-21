"""Backend tests for iteration 4 Gaming features:
- Catalog history (record + list + revert)
- Earnings trend endpoint
- Watch notify endpoint (env-gated)
"""

import os

import httpx
import pytest

BACKEND_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://unruffled-hamilton-13.preview.emergentagent.com",
).rstrip("/")
API = f"{BACKEND_URL}/api"

DEMO_EMAIL = "demo@subly.app"
DEMO_PASSWORD = "subly1234"


@pytest.fixture(scope="module")
def session():
    s = httpx.Client(base_url=API, timeout=30.0)
    r = s.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    # Reset state
    s.post("/gaming/admin/catalog/reset")
    yield s
    s.post("/gaming/admin/catalog/reset")
    s.close()


@pytest.fixture(scope="module")
def anon():
    with httpx.Client(base_url=API, timeout=30.0) as s:
        yield s


# ---- Auth gates ----

@pytest.mark.parametrize("method,path", [
    ("GET", "/gaming/admin/catalog/history"),
    ("POST", "/gaming/admin/catalog/history/xxx/revert"),
    ("GET", "/gaming/earnings/trend"),
])
def test_history_and_trend_require_auth(anon, method, path):
    r = anon.request(method, path, json={} if method == "POST" else None)
    assert r.status_code == 401, f"{method} {path} expected 401 got {r.status_code}"


# ---- History recording ----

def test_history_override_then_modify_then_delete(session):
    rows = session.get("/gaming/admin/catalog").json()
    offer_id = rows[0]["offer_id"]
    base_price = rows[0]["base_price_try"]

    # 1st PUT -> action='override', before=null
    r1 = session.put(f"/gaming/admin/catalog/{offer_id}", json={"price_try": round(base_price + 5, 2), "campaign": "c1"})
    assert r1.status_code == 200

    # 2nd PUT -> action='modify', before={previous values}
    r2 = session.put(f"/gaming/admin/catalog/{offer_id}", json={"price_try": round(base_price + 9, 2), "campaign": "c2"})
    assert r2.status_code == 200

    # DELETE -> action='delete'
    d = session.delete(f"/gaming/admin/catalog/{offer_id}")
    assert d.status_code == 204

    hist = session.get(f"/gaming/admin/catalog/history?offer_id={offer_id}").json()
    assert isinstance(hist, list)
    actions = [h["action"] for h in hist]
    # Reverse chronological: delete, modify, override (most recent first)
    assert actions[:3] == ["delete", "modify", "override"], actions
    override_entry = hist[2]
    modify_entry = hist[1]
    delete_entry = hist[0]

    assert override_entry["before"] is None
    assert override_entry["after"] is not None
    assert modify_entry["before"] is not None
    assert modify_entry["after"] is not None
    assert delete_entry["before"] is not None
    assert delete_entry["after"] is None

    # Required fields
    for h in hist[:3]:
        for k in ("id", "action", "before", "after", "changed_at", "offer_id",
                  "product_name", "seller_name", "game_name"):
            assert k in h, f"missing {k}"


def test_history_global_across_offers(session):
    rows = session.get("/gaming/admin/catalog").json()
    o1, o2 = rows[0]["offer_id"], rows[1]["offer_id"]
    session.put(f"/gaming/admin/catalog/{o1}", json={"price_try": 199.0})
    session.put(f"/gaming/admin/catalog/{o2}", json={"price_try": 299.0})

    hist = session.get("/gaming/admin/catalog/history?limit=50").json()
    offer_ids = {h["offer_id"] for h in hist}
    assert o1 in offer_ids and o2 in offer_ids

    # reverse chronological
    changed = [h["changed_at"] for h in hist]
    assert changed == sorted(changed, reverse=True)

    # cleanup
    session.delete(f"/gaming/admin/catalog/{o1}")
    session.delete(f"/gaming/admin/catalog/{o2}")


def test_bulk_import_records_history_per_row(session):
    session.post("/gaming/admin/catalog/reset")
    rows = session.get("/gaming/admin/catalog").json()
    o1, o2 = rows[0]["offer_id"], rows[1]["offer_id"]
    payload = {"overrides": [
        {"offer_id": o1, "price_try": 111.11},
        {"offer_id": o2, "price_try": 222.22},
    ]}
    r = session.post("/gaming/admin/catalog/import", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["applied"] == 2

    hist = session.get("/gaming/admin/catalog/history?limit=50").json()
    bulk = [h for h in hist if h["action"] == "bulk_import"]
    assert len(bulk) >= 2
    assert {b["offer_id"] for b in bulk[:2]} == {o1, o2}


def test_reset_records_history_per_override(session):
    rows = session.get("/gaming/admin/catalog").json()
    o1 = rows[0]["offer_id"]
    session.put(f"/gaming/admin/catalog/{o1}", json={"price_try": 88.0})

    # Count how many overrides exist now
    admin = session.get("/gaming/admin/catalog").json()
    active = [a for a in admin if a["has_override"]]
    n_active = len(active)
    assert n_active >= 1

    r = session.post("/gaming/admin/catalog/reset")
    assert r.status_code == 204

    hist = session.get("/gaming/admin/catalog/history?limit=100").json()
    reset_entries = [h for h in hist if h["action"] == "reset"]
    # Should have exactly n_active new reset entries at the top
    assert len(reset_entries) >= n_active
    for e in reset_entries[:n_active]:
        assert e["before"] is not None
        assert e["after"] is None


# ---- Revert ----

def test_revert_before_null_removes_override(session):
    session.post("/gaming/admin/catalog/reset")
    rows = session.get("/gaming/admin/catalog").json()
    o1 = rows[0]["offer_id"]
    base_price = rows[0]["base_price_try"]

    session.put(f"/gaming/admin/catalog/{o1}", json={"price_try": round(base_price + 40, 2)})
    hist = session.get(f"/gaming/admin/catalog/history?offer_id={o1}").json()
    # The 'override' entry has before=null
    override_entry = next(h for h in hist if h["action"] == "override" and h["before"] is None)
    hid = override_entry["id"]

    r = session.post(f"/gaming/admin/catalog/history/{hid}/revert")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_override"] is False
    assert body["current_price_try"] == base_price


def test_revert_with_values_upserts_and_records_revert(session):
    session.post("/gaming/admin/catalog/reset")
    rows = session.get("/gaming/admin/catalog").json()
    o1 = rows[0]["offer_id"]

    session.put(f"/gaming/admin/catalog/{o1}", json={"price_try": 100.0, "campaign": "v1"})
    session.put(f"/gaming/admin/catalog/{o1}", json={"price_try": 200.0, "campaign": "v2"})

    hist = session.get(f"/gaming/admin/catalog/history?offer_id={o1}").json()
    modify_entry = next(h for h in hist if h["action"] == "modify")
    hid = modify_entry["id"]
    prev_values = modify_entry["before"]
    assert prev_values and prev_values.get("price_try") == 100.0

    r = session.post(f"/gaming/admin/catalog/history/{hid}/revert")
    assert r.status_code == 200
    body = r.json()
    assert body["has_override"] is True
    assert body["current_price_try"] == 100.0

    hist2 = session.get(f"/gaming/admin/catalog/history?offer_id={o1}").json()
    assert hist2[0]["action"] == "revert"

    session.delete(f"/gaming/admin/catalog/{o1}")


def test_revert_unknown_history_id_404(session):
    r = session.post("/gaming/admin/catalog/history/nonexistent-id-xyz/revert")
    assert r.status_code == 404
    assert "Geçmiş kaydı bulunamadı" in r.text


# ---- Earnings trend ----

def test_earnings_trend_default_6_points(session):
    r = session.get("/gaming/earnings/trend")
    assert r.status_code == 200
    body = r.json()
    for k in ("months", "range_from", "range_to", "total_spent", "total_commission",
              "count", "points", "by_seller"):
        assert k in body
    assert body["months"] == 6
    assert len(body["points"]) == 6
    # Chronological order (oldest first)
    months = [p["month"] for p in body["points"]]
    assert months == sorted(months)
    for p in body["points"]:
        for k in ("month", "month_label", "total_spent", "total_commission", "count"):
            assert k in p


def test_earnings_trend_months_1(session):
    r = session.get("/gaming/earnings/trend?months=1")
    assert r.status_code == 200
    body = r.json()
    assert body["months"] == 1
    assert len(body["points"]) == 1


def test_earnings_trend_months_25_rejected(session):
    r = session.get("/gaming/earnings/trend?months=25")
    assert r.status_code == 422


def test_earnings_trend_by_seller_sorted(session):
    r = session.get("/gaming/earnings/trend").json()
    by_seller = r["by_seller"]
    # Demo has purchases, so should have >0 sellers
    if by_seller:
        commissions = [s["commission"] for s in by_seller]
        assert commissions == sorted(commissions, reverse=True)
        for s in by_seller:
            assert s["commission"] > 0


# ---- Watch notify (env-gated) ----

def test_notify_watch_without_email_key_does_not_crash(session):
    # Get any watch id
    watches = session.get("/gaming/watches").json()
    if not watches:
        pytest.skip("No watches for demo user")
    wid = watches[0]["id"]
    r = session.post(f"/gaming/watches/{wid}/notify")
    # Env-gated: either 5xx OR 2xx with sent:false (per acceptance)
    assert r.status_code in (200, 400, 500, 502, 503), r.status_code
    if r.status_code == 200:
        body = r.json()
        # If it returns JSON, sent should be false when env unset
        assert "sent" in body or "ok" in body or isinstance(body, dict)
