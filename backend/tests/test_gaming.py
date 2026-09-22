"""Backend tests for the Gaming module (catalog + purchases -> expenses)."""

import os
import httpx
import pytest

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", os.environ.get("BACKEND_URL", "http://localhost:8001")).rstrip("/")
API = f"{BACKEND_URL}/api"

DEMO_EMAIL = "demo@subly.app"
DEMO_PASSWORD = "subly1234"


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def session():
    s = httpx.Client(base_url=API, timeout=30.0)
    r = s.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    # The session cookie is Secure+SameSite=None (correct for production HTTPS).
    # httpx's cookie jar won't re-attach a Secure cookie to a plain http://
    # localhost request, so subsequent calls on this client would 401 even
    # though login succeeded. Use the Bearer-token fallback get_current_user()
    # already supports instead of weakening the cookie's security attributes.
    s.headers["Authorization"] = f"Bearer {r.cookies.get('session_token')}"
    yield s
    s.close()


@pytest.fixture(scope="module")
def anon():
    with httpx.Client(base_url=API, timeout=30.0) as s:
        yield s


# ---------- auth gate ----------

def test_gaming_home_requires_auth(anon):
    r = anon.get("/gaming/home")
    assert r.status_code == 401

def test_gaming_games_requires_auth(anon):
    assert anon.get("/gaming/games").status_code == 401

def test_gaming_purchase_requires_auth(anon):
    r = anon.post("/gaming/purchases", json={"offer_id": "x", "product_id": "x", "seller_id": "x", "amount_try": 1})
    assert r.status_code == 401


# ---------- catalog ----------

def test_gaming_home_shape(session):
    r = session.get("/gaming/home")
    assert r.status_code == 200
    data = r.json()
    for k in ("all_games", "popular_games", "cheapest_offers", "campaigns", "instant_delivery", "today_deals", "sellers", "catalog_note", "updated_at"):
        assert k in data, f"missing key {k}"
    assert len(data["all_games"]) == 17, f"expected 17 games got {len(data['all_games'])}"
    assert len(data["sellers"]) == 7, f"expected 7 sellers got {len(data['sellers'])}"
    for g in data["all_games"]:
        for k in ("slug", "name", "currency", "category", "accent_color", "icon_url"):
            assert k in g and g[k] is not None
    # cheapest are verified/trusted only
    for d in data["cheapest_offers"]:
        assert d["seller_reliability"] in ("verified", "trusted")
    # today_deals present
    assert len(data["today_deals"]) >= 1


def test_list_games(session):
    r = session.get("/gaming/games")
    assert r.status_code == 200
    games = r.json()
    assert len(games) == 17
    slugs = {g["slug"] for g in games}
    for expected in ("valorant", "league-of-legends", "pubg-mobile", "steam", "playstation", "xbox", "roblox", "fortnite", "minecraft"):
        assert expected in slugs


def test_valorant_detail_offers_sorted(session):
    r = session.get("/gaming/games/valorant")
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == "valorant"
    assert len(data["products"]) >= 3
    # pick a product and validate its offers ordering
    prod_id = data["products"][0]["id"]
    r2 = session.get(f"/gaming/products/{prod_id}")
    assert r2.status_code == 200
    pd = r2.json()
    rank = {"verified": 0, "trusted": 1, "caution": 2}
    prev = (-1, -1)
    for o in pd["offers"]:
        cur = (rank.get(o["seller_reliability"], 3), o["price_try"])
        assert cur >= prev, f"offers not sorted: {pd['offers']}"
        prev = cur


def test_product_not_found(session):
    r = session.get("/gaming/products/does-not-exist")
    assert r.status_code == 404


def test_game_not_found(session):
    r = session.get("/gaming/games/does-not-exist")
    assert r.status_code == 404


def test_sellers(session):
    r = session.get("/gaming/sellers")
    assert r.status_code == 200
    sellers = r.json()
    assert len(sellers) == 7
    for s in sellers:
        assert s["reliability"] in ("verified", "trusted", "caution")
        assert s["return_policy"]


def test_search_valorant(session):
    r = session.get("/gaming/search", params={"q": "valorant"})
    assert r.status_code == 200
    data = r.json()
    assert any(g["slug"] == "valorant" for g in data["games"])
    assert any("valorant" in p["game_name"].lower() or "vp" in p["game_currency"].lower() for p in data["products"])


# ---------- purchases ----------

def _find_offer(session, product_slug_query="valorant"):
    home = session.get("/gaming/home").json()
    # find a Valorant offer via detail
    detail = session.get("/gaming/games/valorant").json()
    prod = detail["products"][2]  # 2050 VP typically
    pd = session.get(f"/gaming/products/{prod['id']}").json()
    offer = pd["offers"][0]
    return offer, pd


def test_purchase_mismatched_offer_returns_400(session):
    offer, pd = _find_offer(session)
    r = session.post("/gaming/purchases", json={
        "offer_id": offer["id"],
        "product_id": "some-other-product",
        "seller_id": offer["seller_id"],
        "amount_try": offer["price_try"],
    })
    assert r.status_code == 400


def test_purchase_creates_expense_and_delete_cascades(session):
    offer, pd = _find_offer(session)
    payload = {
        "offer_id": offer["id"],
        "product_id": pd["id"],
        "seller_id": offer["seller_id"],
        "amount_try": offer["price_try"],
    }
    r = session.post("/gaming/purchases", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "purchase" in body and "monthly_total" in body and "monthly_count" in body
    purchase = body["purchase"]
    assert purchase["amount_try"] == offer["price_try"]
    assert purchase["expense_id"]
    assert purchase["game_name"]
    month = purchase["date"][:7]

    # Verify expense present in /api/expenses
    exp = session.get("/expenses", params={"month": month})
    assert exp.status_code == 200
    exps = exp.json()
    matches = [e for e in exps if e.get("id") == purchase["expense_id"]]
    assert len(matches) == 1, f"expected linked expense not found. sample={exps[:2]}"
    assert matches[0]["category"] == "Gaming"
    assert purchase["game_name"] in matches[0]["title"]

    # Dashboard summary includes it
    ds = session.get("/dashboard/summary")
    assert ds.status_code == 200

    # Gaming summary
    gs = session.get("/gaming/summary", params={"month": month})
    assert gs.status_code == 200
    gsd = gs.json()
    assert gsd["month"] == month
    assert gsd["count"] >= 1
    assert gsd["total"] >= offer["price_try"]
    assert isinstance(gsd["top_games"], list)

    # Delete cascades
    d = session.delete(f"/gaming/purchases/{purchase['id']}")
    assert d.status_code == 204
    # expense gone
    exp2 = session.get("/expenses", params={"month": month})
    assert exp2.status_code == 200
    assert not any(e.get("id") == purchase["expense_id"] for e in exp2.json())
    # deleting again -> 404
    d2 = session.delete(f"/gaming/purchases/{purchase['id']}")
    assert d2.status_code == 404
