"""P0 regression tests: authenticated-user data isolation.

Context: a real bug was found and fixed in this round. Every new account
(register, first login, first Google login) was being seeded with four fake
"starter" subscriptions — Netflix, Spotify, YouTube Premium, Google One — as
if they were the user's own real data (backend/lib/seed.py's
seed_starter_subscriptions(), unconditionally called from every auth path in
routers/auth.py). That bug was not a cross-user leak — each user's seeded
copies were correctly scoped by their own user_id in Mongo — but it
fabricated data and silently presented it as real, which is unacceptable for
a product whose whole job is to tell a user the truth about their own money.
The fix (routers/auth.py's _seed_demo_account_data) restricts that seeding to
the demo account (demo@subly.app) only; every other new account now starts
genuinely empty.

A full manual audit of every user-scoped backend endpoint (subscriptions,
expenses, incomes, bills, budgets, dashboard summary, calendar, savings,
alerts, assistant context, gaming purchases/watches/admin-catalog/earnings,
account export, digest) found every single Mongo query already correctly
filtered by user_id — no cross-user leak was found anywhere. These tests
exist to make both classes of bug — fabricated data presented as real, and
genuine cross-user leakage — regressions that fail CI, not things a human has
to notice by eye in production.

Each test in this file registers its own brand-new, uniquely-emailed account
via the `new_user` / `make_user` fixtures (see conftest.py) — never the
shared demo account — so tests are independent and order-safe.
"""

from datetime import date

STARTER_NAMES = {"Netflix", "Spotify", "YouTube Premium", "Google One"}


def _today() -> str:
    return date.today().isoformat()


def _sub_payload(name: str, price: float = 99.0) -> dict:
    return {
        "name": name,
        "category": "Eğlence",
        "price": price,
        "currency": "TRY",
        "renewal_date": _today(),
        "payment_method": "Kart •••• 4821",
        "cancellation_url": "https://example.com/cancel",
    }


def _expense_payload(title: str, amount: float = 100.0) -> dict:
    return {"title": title, "amount": amount, "category": "Market", "date": _today(), "payment_method": "Nakit", "note": ""}


def _income_payload(source: str, amount: float = 1000.0) -> dict:
    return {"source": source, "amount": amount, "kind": "regular", "date": _today(), "note": ""}


def _bill_payload(provider: str, amount: float = 200.0) -> dict:
    return {"provider": provider, "bill_type": "Elektrik", "amount": amount, "due_date": _today(), "frequency": "monthly", "payment_method": "Havale / EFT"}


def _budget_payload(category: str, limit: float = 500.0) -> dict:
    return {"category": category, "limit": limit, "month": ""}


# ===================== TEST A =====================
# New account, zero subscriptions added: must be genuinely empty, and must
# never surface the fabricated starter subscriptions.

def test_a_new_account_has_no_subscriptions_and_no_fake_starter_data(new_user):
    subs = new_user.get("/subscriptions")
    assert subs.status_code == 200
    subs_body = subs.json()
    assert subs_body == [], f"brand-new account must have zero subscriptions, got: {subs_body}"

    names = {s["name"] for s in subs_body}
    leaked = names & STARTER_NAMES
    assert not leaked, f"fake starter subscriptions leaked into a brand-new account: {leaked}"

    summary = new_user.get("/dashboard/summary")
    assert summary.status_code == 200
    upcoming = summary.json().get("upcoming", [])
    upcoming_titles = {u["title"] for u in upcoming}
    assert not (upcoming_titles & STARTER_NAMES), f"fake starter subscriptions leaked into upcoming payments: {upcoming_titles}"
    sub_upcoming = [u for u in upcoming if u.get("kind") == "subscription"]
    assert sub_upcoming == [], f"a subscription-less new account must have zero subscription-kind upcoming payments, got: {sub_upcoming}"


# ===================== TEST B =====================
# A user who genuinely adds Netflix must see it.

def test_b_user_sees_their_own_added_subscription(new_user):
    r = new_user.post("/subscriptions", json=_sub_payload("Netflix", 229.99))
    assert r.status_code == 200  # subscriptions.create_subscription has no explicit status_code (defaults to 200), unlike lib/crud.py's 201
    subs = new_user.get("/subscriptions").json()
    assert any(s["name"] == "Netflix" for s in subs)


# ===================== TEST C =====================
# A second, independent new account must not see the first account's data.

def test_c_second_account_does_not_see_first_accounts_subscription(make_user):
    user_a = make_user("isoA")
    user_a.post("/subscriptions", json=_sub_payload("Netflix", 229.99))

    user_b = make_user("isoB")
    subs_b = user_b.get("/subscriptions").json()
    assert subs_b == [], f"a fresh second account must start empty, got: {subs_b}"
    assert not any(s["name"] == "Netflix" for s in subs_b)


# ===================== TEST D =====================
# Two users, two different subscriptions: each sees only their own.

def test_d_two_users_see_only_their_own_subscription(make_user):
    user_a = make_user("isoA")
    user_b = make_user("isoB")
    user_a.post("/subscriptions", json=_sub_payload("Netflix", 229.99))
    user_b.post("/subscriptions", json=_sub_payload("Spotify", 99.99))

    names_a = {s["name"] for s in user_a.get("/subscriptions").json()}
    names_b = {s["name"] for s in user_b.get("/subscriptions").json()}
    assert names_a == {"Netflix"}
    assert names_b == {"Spotify"}


# ===================== TEST E =====================
# The same isolation, generalized across expenses/incomes/bills/budgets.

def test_e_expenses_are_isolated_between_users(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    user_a.post("/expenses", json=_expense_payload("A-only expense"))
    assert user_b.get("/expenses").json() == []
    titles_a = {e["title"] for e in user_a.get("/expenses").json()}
    assert titles_a == {"A-only expense"}


def test_e_incomes_are_isolated_between_users(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    user_a.post("/incomes", json=_income_payload("A-only income"))
    assert user_b.get("/incomes").json() == []
    sources_a = {i["source"] for i in user_a.get("/incomes").json()}
    assert sources_a == {"A-only income"}


def test_e_bills_are_isolated_between_users(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    user_a.post("/bills", json=_bill_payload("A-only bill"))
    assert user_b.get("/bills").json() == []
    providers_a = {b["provider"] for b in user_a.get("/bills").json()}
    assert providers_a == {"A-only bill"}


def test_e_budgets_are_isolated_between_users(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    user_a.post("/budgets", json=_budget_payload("Market"))
    assert user_b.get("/budgets").json() == []
    categories_a = {b["category"] for b in user_a.get("/budgets").json()}
    assert categories_a == {"Market"}


def test_e_savings_report_unused_count_is_isolated_between_users(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    payload = _sub_payload("UnusedSub", 49.0)
    payload["usage"] = "unused"
    user_a.post("/subscriptions", json=payload)

    savings_a = user_a.get("/savings").json()
    savings_b = user_b.get("/savings").json()
    assert savings_a["unused_subscriptions"] >= 1
    assert savings_b["unused_subscriptions"] == 0


# ===================== TEST F =====================
# User B must not be able to read/update/delete User A's records by ID.

def test_f_user_b_cannot_update_or_delete_user_as_subscription(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    created = user_a.post("/subscriptions", json=_sub_payload("Netflix", 229.99)).json()
    sub_id = created["id"]

    r_update = user_b.patch(f"/subscriptions/{sub_id}", json={"price": 1.0})
    assert r_update.status_code == 404, f"User B updated User A's subscription: {r_update.status_code} {r_update.text}"

    r_delete = user_b.delete(f"/subscriptions/{sub_id}")
    assert r_delete.status_code == 404, f"User B deleted User A's subscription: {r_delete.status_code} {r_delete.text}"

    still_there = [s for s in user_a.get("/subscriptions").json() if s["id"] == sub_id]
    assert still_there and still_there[0]["price"] == 229.99, "User A's subscription must be untouched by User B's attempts"


def test_f_user_b_cannot_update_or_delete_user_as_expense(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    created = user_a.post("/expenses", json=_expense_payload("A-only expense")).json()
    expense_id = created["id"]

    assert user_b.patch(f"/expenses/{expense_id}", json={"amount": 1.0}).status_code == 404
    assert user_b.delete(f"/expenses/{expense_id}").status_code == 404

    still_there = [e for e in user_a.get("/expenses").json() if e["id"] == expense_id]
    assert still_there and still_there[0]["amount"] == 100.0


def test_f_user_b_cannot_update_or_delete_user_as_bill(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    created = user_a.post("/bills", json=_bill_payload("A-only bill")).json()
    bill_id = created["id"]

    assert user_b.patch(f"/bills/{bill_id}", json={"amount": 1.0}).status_code == 404
    assert user_b.delete(f"/bills/{bill_id}").status_code == 404

    still_there = [b for b in user_a.get("/bills").json() if b["id"] == bill_id]
    assert still_there and still_there[0]["amount"] == 200.0


def test_f_user_b_cannot_update_or_delete_user_as_budget(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    created = user_a.post("/budgets", json=_budget_payload("Market")).json()
    budget_id = created["id"]

    assert user_b.patch(f"/budgets/{budget_id}", json={"limit": 1.0}).status_code == 404
    assert user_b.delete(f"/budgets/{budget_id}").status_code == 404

    still_there = [b for b in user_a.get("/budgets").json() if b["id"] == budget_id]
    assert still_there and still_there[0]["limit"] == 500.0


def test_f_user_b_cannot_update_or_delete_user_as_income(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    created = user_a.post("/incomes", json=_income_payload("A-only income")).json()
    income_id = created["id"]

    assert user_b.patch(f"/incomes/{income_id}", json={"amount": 1.0}).status_code == 404
    assert user_b.delete(f"/incomes/{income_id}").status_code == 404

    still_there = [i for i in user_a.get("/incomes").json() if i["id"] == income_id]
    assert still_there and still_there[0]["amount"] == 1000.0


# ===================== Section 11: account export isolation =====================

def test_account_export_contains_only_the_authenticated_users_own_data(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    user_a.post("/subscriptions", json=_sub_payload("Netflix", 229.99))
    user_a.post("/expenses", json=_expense_payload("A-only expense"))
    user_a.post("/incomes", json=_income_payload("A-only income"))
    user_a.post("/bills", json=_bill_payload("A-only bill"))
    user_a.post("/budgets", json=_budget_payload("Market"))

    user_b.post("/subscriptions", json=_sub_payload("Spotify", 99.99))

    export_a = user_a.get("/account/export")
    assert export_a.status_code == 200
    body_a = export_a.json()
    assert {s["name"] for s in body_a["subscriptions"]} == {"Netflix"}
    assert {e["title"] for e in body_a["expenses"]} == {"A-only expense"}
    assert {i["source"] for i in body_a["incomes"]} == {"A-only income"}
    assert {b["provider"] for b in body_a["bills"]} == {"A-only bill"}
    assert {b["category"] for b in body_a["budgets"]} == {"Market"}
    assert body_a["user"]["user_id"] != user_b.get("/auth/me").json()["user_id"]

    export_b = user_b.get("/account/export")
    body_b = export_b.json()
    assert {s["name"] for s in body_b["subscriptions"]} == {"Spotify"}
    assert body_b["expenses"] == [] and body_b["incomes"] == [] and body_b["bills"] == [] and body_b["budgets"] == []


# ===================== Section 12: alerts / calendar isolation =====================

def test_alerts_and_calendar_do_not_leak_between_users(make_user):
    user_a, user_b = make_user("isoA"), make_user("isoB")
    user_a.post("/subscriptions", json=_sub_payload("Netflix", 229.99))

    alerts_b = user_b.get("/alerts")
    assert alerts_b.status_code == 200
    for alert in alerts_b.json():
        assert "Netflix" not in alert.get("message", ""), f"User A's Netflix leaked into User B's alerts: {alert}"

    month = date.today().isoformat()[:7]
    calendar_b = user_b.get(f"/calendar?month={month}")
    assert calendar_b.status_code == 200
    events_b = calendar_b.json().get("events", [])
    assert not any("Netflix" in e.get("title", "") for e in events_b), f"User A's Netflix leaked into User B's calendar: {events_b}"

    calendar_a = user_a.get(f"/calendar?month={month}")
    events_a = calendar_a.json().get("events", [])
    assert any("Netflix" in e.get("title", "") for e in events_a), "User A's own Netflix renewal should appear in their own calendar"
