"""Backend tests for Gaming next-gen features: admin catalog editor, price watches,
affiliate earnings, and gaming monthly budget."""

import os
import io
import uuid
from datetime import datetime, timezone

import httpx
import pytest

BACKEND_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    os.environ.get("BACKEND_URL", "http://localhost:8001"),
).rstrip("/")
API = f"{BACKEND_URL}/api"

DEMO_EMAIL = "demo@subly.app"
DEMO_PASSWORD = "subly1234"


@pytest.fixture(scope="module")
def session():
    # A fresh, isolated user instead of the shared demo account: this module and
    # test_gaming_iter4.py both write to the demo account's gaming catalog
    # overrides, and pytest.ini runs different modules in parallel xdist workers
    # (loadscope only serializes *within* a module) — sharing the demo account's
    # override state caused real cross-module races. Each module gets its own
    # account so there is no shared mutable state to race on.
    s = httpx.Client(base_url=API, timeout=30.0)
    email = f"gaming-nextgen-{uuid.uuid4().hex[:12]}@example.com"
    r = s.post("/auth/register", json={"name": "Gaming Nextgen Test", "email": email, "password": "TestPass123!"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    # The session cookie is Secure+SameSite=None (correct for production HTTPS);
    # httpx's cookie jar won't re-attach it to a plain http://localhost request,
    # so use the Bearer-token fallback get_current_user() already supports.
    s.headers["Authorization"] = f"Bearer {r.cookies.get('session_token')}"
    # Clean state
    s.post("/gaming/admin/catalog/reset")
    s.delete("/gaming/budget")
    yield s
    # Teardown
    s.post("/gaming/admin/catalog/reset")
    s.delete("/gaming/budget")
    try:
        s.delete("/account")  # self-delete only; leaves no orphan test account behind
    except Exception:
        pass
    s.close()


@pytest.fixture(scope="module")
def anon():
    with httpx.Client(base_url=API, timeout=30.0) as s:
        yield s


# ---------- Auth gates ----------

@pytest.mark.parametrize("method,path", [
    ("GET", "/gaming/admin/catalog"),
    ("GET", "/gaming/watches"),
    ("GET", "/gaming/earnings"),
    ("GET", "/gaming/earnings/all"),
    ("GET", "/gaming/budget"),
    ("PUT", "/gaming/budget"),
    ("DELETE", "/gaming/budget"),
])
def test_endpoints_require_auth(anon, method, path):
    r = anon.request(method, path, json={} if method in ("PUT", "POST") else None)
    assert r.status_code == 401, f"{method} {path} expected 401, got {r.status_code}"


# ---------- Admin catalog ----------

def test_admin_catalog_list_shape(session):
    r = session.get("/gaming/admin/catalog")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert 150 <= len(rows) <= 200, f"expected ~162 rows, got {len(rows)}"
    row = rows[0]
    for key in ("offer_id", "product_id", "game_slug", "game_name", "product_name",
                "seller_id", "seller_name", "seller_reliability",
                "base_price_try", "current_price_try", "has_override"):
        assert key in row, f"missing {key} in admin row"
    # Initially no overrides
    assert all(r["has_override"] is False for r in rows)


def test_admin_catalog_put_and_delete_override(session):
    rows = session.get("/gaming/admin/catalog").json()
    row = rows[0]
    offer_id = row["offer_id"]
    new_price = round(row["base_price_try"] + 12.34, 2)

    r = session.put(f"/gaming/admin/catalog/{offer_id}", json={
        "price_try": new_price,
        "delivery": "Anında",
        "campaign": "Test kampanya",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_override"] is True
    assert data["current_price_try"] == new_price
    assert data["current_campaign"] == "Test kampanya"

    # GET reflects override
    rows2 = session.get("/gaming/admin/catalog").json()
    match = next(x for x in rows2 if x["offer_id"] == offer_id)
    assert match["has_override"] is True
    assert match["current_price_try"] == new_price

    # DELETE
    d = session.delete(f"/gaming/admin/catalog/{offer_id}")
    assert d.status_code == 204
    rows3 = session.get("/gaming/admin/catalog").json()
    match = next(x for x in rows3 if x["offer_id"] == offer_id)
    assert match["has_override"] is False
    assert match["current_price_try"] == row["base_price_try"]


def test_admin_catalog_put_unknown_returns_404_with_turkish_detail(session):
    r = session.put("/gaming/admin/catalog/does-not-exist", json={"price_try": 100})
    assert r.status_code == 404
    assert r.json().get("detail") == "Teklif bulunamadı"


def test_admin_catalog_import_json(session):
    rows = session.get("/gaming/admin/catalog").json()
    good = rows[1]["offer_id"]
    payload = {
        "overrides": [
            {"offer_id": good, "price_try": 42.5},
            {"offer_id": "unknown-offer-xyz", "price_try": 100.0},
        ]
    }
    r = session.post("/gaming/admin/catalog/import", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == 1
    assert data["skipped"] == 1
    assert len(data["errors"]) >= 1
    # cleanup
    session.delete(f"/gaming/admin/catalog/{good}")


def test_admin_catalog_import_csv(session):
    rows = session.get("/gaming/admin/catalog").json()
    offer_a = rows[2]["offer_id"]
    offer_b = rows[3]["offer_id"]
    csv_body = (
        "offer_id,price_try,original_price_try,delivery,campaign,url\n"
        f"{offer_a},99.99,120.00,Anında,Deneme,\n"
        f"{offer_b},77.50,,1-5 dk,,\n"
    )
    files = {"file": ("import.csv", io.BytesIO(csv_body.encode("utf-8")), "text/csv")}
    r = session.post("/gaming/admin/catalog/import/csv", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == 2
    rows2 = session.get("/gaming/admin/catalog").json()
    a = next(x for x in rows2 if x["offer_id"] == offer_a)
    b = next(x for x in rows2 if x["offer_id"] == offer_b)
    assert a["current_price_try"] == 99.99
    assert b["current_price_try"] == 77.50
    # cleanup
    session.post("/gaming/admin/catalog/reset")


def test_admin_catalog_reset(session):
    rows = session.get("/gaming/admin/catalog").json()
    offer_id = rows[0]["offer_id"]
    session.put(f"/gaming/admin/catalog/{offer_id}", json={"price_try": 55.55})
    r = session.post("/gaming/admin/catalog/reset")
    assert r.status_code == 204
    rows2 = session.get("/gaming/admin/catalog").json()
    assert all(r["has_override"] is False for r in rows2)


def test_override_reflected_in_product_detail(session):
    # Find a Valorant product and override the cheapest offer
    detail = session.get("/gaming/games/valorant").json()
    prod_id = detail["products"][0]["id"]
    pd = session.get(f"/gaming/products/{prod_id}").json()
    cheapest = pd["offers"][0]
    new_price = round(cheapest["price_try"] - 20.0, 2)
    r = session.put(f"/gaming/admin/catalog/{cheapest['id']}", json={"price_try": new_price})
    assert r.status_code == 200

    pd2 = session.get(f"/gaming/products/{prod_id}").json()
    match = next(o for o in pd2["offers"] if o["id"] == cheapest["id"])
    assert match["has_override"] is True
    assert match["price_try"] == new_price
    # cleanup
    session.delete(f"/gaming/admin/catalog/{cheapest['id']}")


# ---------- Affiliate ----------

def test_affiliate_params_in_urls(session):
    home = session.get("/gaming/home").json()
    for deal in home["cheapest_offers"] + home["campaigns"] + home["today_deals"]:
        u = deal["url"]
        assert ("ref=" in u) or ("aff=" in u) or ("utm_source=" in u), f"missing affiliate param: {u}"

    # product detail
    detail = session.get("/gaming/games/valorant").json()
    prod_id = detail["products"][0]["id"]
    pd = session.get(f"/gaming/products/{prod_id}").json()
    for o in pd["offers"]:
        u = o["url"]
        assert ("ref=" in u) or ("aff=" in u) or ("utm_source=" in u)


def test_estimated_commission_matches_rate(session):
    detail = session.get("/gaming/games/valorant").json()
    prod_id = detail["products"][0]["id"]
    pd = session.get(f"/gaming/products/{prod_id}").json()
    rates = {"gamesatis": 0.04, "bynogame": 0.05, "oyunfor": 0.035,
             "hesap-com-tr": 0.03, "trendyol": 0.02, "hepsiburada": 0.02,
             "turkcell-pasaj": 0.025}
    for o in pd["offers"]:
        expected = round(o["price_try"] * rates.get(o["seller_id"], 0.0), 2)
        assert o["estimated_commission_try"] == expected


# ---------- Purchases → commission + earnings ----------

def test_purchase_records_commission_and_earnings(session):
    detail = session.get("/gaming/games/valorant").json()
    prod_id = detail["products"][1]["id"]
    pd = session.get(f"/gaming/products/{prod_id}").json()
    offer = pd["offers"][0]
    r = session.post("/gaming/purchases", json={
        "offer_id": offer["id"],
        "product_id": pd["id"],
        "seller_id": offer["seller_id"],
        "amount_try": offer["price_try"],
    })
    assert r.status_code == 201, r.text
    purchase = r.json()["purchase"]
    assert purchase.get("estimated_commission_try") is not None
    assert purchase["estimated_commission_try"] > 0
    assert purchase.get("commission_rate") is not None
    assert purchase["commission_rate"] > 0

    month = purchase["date"][:7]

    # Earnings monthly
    e = session.get("/gaming/earnings", params={"month": month})
    assert e.status_code == 200
    edata = e.json()
    for key in ("month", "month_label", "total_spent", "total_commission", "count", "by_seller"):
        assert key in edata
    assert edata["count"] >= 1
    assert edata["total_commission"] > 0

    # Earnings all-time
    ea = session.get("/gaming/earnings/all")
    assert ea.status_code == 200
    assert ea.json()["total_commission"] > 0

    # cleanup
    session.delete(f"/gaming/purchases/{purchase['id']}")


# ---------- Watches ----------

def test_watch_create_list_update_delete(session):
    detail = session.get("/gaming/games/valorant").json()
    prod_id = detail["products"][0]["id"]
    pd = session.get(f"/gaming/products/{prod_id}").json()
    cur_price = pd["offers"][0]["price_try"]

    # target ABOVE current -> triggered=True immediately
    r = session.post("/gaming/watches", json={
        "product_id": prod_id,
        "target_price_try": cur_price + 50,
    })
    assert r.status_code == 201, r.text
    w = r.json()
    assert w["triggered"] is True
    assert w["best_offer_url"]
    assert ("ref=" in w["best_offer_url"]) or ("aff=" in w["best_offer_url"]) or ("utm_source=" in w["best_offer_url"])
    watch_id = w["id"]

    # GET list
    lst = session.get("/gaming/watches").json()
    assert any(x["id"] == watch_id for x in lst)

    # Alerts include watch
    alerts = session.get("/alerts").json()
    watch_alert_ids = [a for a in alerts if isinstance(a, dict) and a.get("id", "").startswith("gaming-watch-")]
    assert len(watch_alert_ids) >= 1, f"expected gaming-watch alert, alerts={alerts[:3]}"

    # PATCH to un-trigger (target below current)
    r2 = session.patch(f"/gaming/watches/{watch_id}", json={"target_price_try": max(1.0, cur_price - 100)})
    assert r2.status_code == 200
    assert r2.json()["triggered"] is False

    # DELETE
    d = session.delete(f"/gaming/watches/{watch_id}")
    assert d.status_code == 204
    lst2 = session.get("/gaming/watches").json()
    assert not any(x["id"] == watch_id for x in lst2)


# ---------- Budget ----------

def test_budget_lifecycle(session):
    session.delete("/gaming/budget")
    # unset
    r = session.get("/gaming/budget")
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] is None
    assert "spent" in data and "percent" in data and "exceeded" in data

    # set
    r = session.put("/gaming/budget", json={"limit": 100000})
    assert r.status_code == 200
    d = r.json()
    assert d["limit"] == 100000
    assert d["exceeded"] is False

    # small limit -> exceeded (assuming demo has purchases)
    r = session.put("/gaming/budget", json={"limit": 1})
    d = r.json()
    # If demo has spent >0 this month -> exceeded True
    if d["spent"] > 1:
        assert d["exceeded"] is True

    # clear
    r = session.delete("/gaming/budget")
    assert r.status_code == 204
    r = session.get("/gaming/budget")
    assert r.json()["limit"] is None
