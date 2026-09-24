"""Subscription hub: ownership, provider catalog, manual add, discovery candidates,
duplicates, legacy rows and insights. Runs the real routers against the in-memory
test store (tests/isolated_store.py) — no real database, mailbox or bank is touched."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from isolated_store import create_app
from lib import finance, provider_catalog
from lib.db import db
from lib.discovery import candidates as candidate_service
from lib.discovery.email_source import EmailMessageMeta, classify_email
from lib.discovery.importer import parse_amount, parse_statement
from lib.discovery.transactions import Transaction, detect_recurring


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


def sub(name, **extra):
    return {"name": name, "category": "Eğlence", "price": 100, "currency": "TRY", "renewal_date": finance.today().isoformat(), "billing_cycle": "monthly", **extra}


def statement(*rows):
    return "\n".join(rows)


def monthly_rows(descriptor, amount, count=3, start=None):
    start = start or finance.today() - timedelta(days=30 * count)
    return [f"{finance.add_months(start, i).isoformat()};{descriptor};{amount}" for i in range(count)]


def user_id(client):
    return client.get("/api/auth/me").json()["user_id"]


# ---- 1. data correctness for new accounts ---------------------------------------


def test_new_user_starts_with_nothing(clients):
    for client in clients:
        assert client.get("/api/subscriptions").json() == []
        assert client.get("/api/subscriptions/candidates").json() == []
        ins = client.get("/api/subscriptions/insights").json()
        assert (ins["active_count"], ins["monthly_total_try"], ins["yearly_projection_try"], ins["unused_count"]) == (0, 0, 0, 0)
        summary = client.get("/api/dashboard/summary").json()
        assert summary["subscription_monthly"] == 0 and summary["subscription_yearly"] == 0


# ---- ownership --------------------------------------------------------------------


def test_foreign_subscription_id_cannot_be_read_changed_reviewed_or_deleted(clients):
    a, b = clients
    created = a.post("/api/subscriptions", json=sub("Netflix", provider_id="netflix")).json()
    assert b.get("/api/subscriptions").json() == []
    assert a.get(f"/api/subscriptions/{created['id']}").status_code == 200
    assert b.get(f"/api/subscriptions/{created['id']}").status_code == 404
    assert b.patch(f"/api/subscriptions/{created['id']}", json={"price": 1}).status_code == 404
    assert b.post(f"/api/subscriptions/{created['id']}/review").status_code == 404
    assert b.delete(f"/api/subscriptions/{created['id']}").status_code == 404
    assert a.get(f"/api/subscriptions/{created['id']}").json()["price"] == 100
    for path in ("insights", "duplicates?name=Netflix"):
        assert "Netflix" not in b.get(f"/api/subscriptions/{path}").text


# ---- 2/3. provider catalog + manual add ---------------------------------------------


def test_catalog_covers_requested_services():
    required = ["netflix", "prime-video", "max", "disney-plus", "apple-tv-plus", "mubi", "exxen", "gain", "tod", "spotify", "apple-music", "youtube-music", "deezer", "tidal",
                "chatgpt-plus", "chatgpt-pro", "claude-pro", "claude-max", "google-gemini", "perplexity-pro", "microsoft-copilot", "github-copilot", "google-one", "icloud-plus",
                "microsoft-365", "dropbox", "adobe-creative-cloud", "canva-pro", "notion", "grammarly", "playstation-plus", "xbox-game-pass", "nintendo-switch-online", "ea-play",
                "github", "jetbrains", "vercel", "cursor", "youtube-premium", "amazon-prime"]
    assert [pid for pid in required if pid not in provider_catalog.PROVIDERS_BY_ID] == []
    for p in provider_catalog.PROVIDERS:
        assert p["pricing"] == {"status": "not_tracked"}  # no invented list prices
        assert p["manage_url"].startswith("https://")


@pytest.mark.parametrize("query, expected", [("ChatGPT", {"chatgpt-plus", "chatgpt-pro"}), ("Prime", {"prime-video", "amazon-prime"}), ("Claude", {"claude-pro", "claude-max"}), ("blutv", {"max"}), ("bein connect", {"tod"})])
def test_provider_search(clients, query, expected):
    ids = [p["id"] for p in clients[0].get(f"/api/subscriptions/providers?q={query}").json()]
    assert expected <= set(ids)
    assert clients[0].get("/api/subscriptions").json() == []  # searching never creates data


def test_provider_search_max_ranks_max_first(clients):
    assert clients[0].get("/api/subscriptions/providers?q=max").json()[0]["id"] == "max"


def test_manual_add_is_always_source_manual_and_uses_provider_manage_url(clients):
    a, _ = clients
    created = a.post("/api/subscriptions", json=sub("ChatGPT Plus", provider_id="chatgpt-plus", plan="Plus", price=20, currency="USD", note="iş", source="email", cancellation_url="")).json()
    assert created["source"] == "manual"  # a client cannot claim e-mail verification
    assert created["legacy"] is False and created["provider_id"] == "chatgpt-plus" and created["plan"] == "Plus" and created["note"] == "iş"
    assert created["cancellation_url"] == provider_catalog.PROVIDERS_BY_ID["chatgpt-plus"]["manage_url"]


def test_manual_add_validation(clients):
    a, _ = clients
    assert a.post("/api/subscriptions", json=sub("Netflix", renewal_date="2026-02-30")).status_code == 422
    assert a.post("/api/subscriptions", json=sub("Netflix", provider_id="not-a-provider")).status_code == 422
    assert a.post("/api/subscriptions", json=sub("Netflix", billing_cycle="weekly")).status_code == 422
    assert a.post("/api/subscriptions", json=sub("Netflix", status="deleted")).status_code == 422
    created = a.post("/api/subscriptions", json=sub("Netflix")).json()
    assert a.patch(f"/api/subscriptions/{created['id']}", json={"renewal_date": "2026-13-01"}).status_code == 422
    assert a.get("/api/subscriptions").json()[0]["renewal_date"] == created["renewal_date"]


def test_manual_duplicate_is_flagged_not_silently_added(clients):
    a, _ = clients
    a.post("/api/subscriptions", json=sub("Netflix", provider_id="netflix"))
    conflict = a.post("/api/subscriptions", json=sub("Netflix"))
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "possible_duplicate"
    assert len(a.get("/api/subscriptions").json()) == 1
    assert a.post("/api/subscriptions", json=sub("Netflix", confirm_duplicate=True)).status_code == 200
    assert len(a.get("/api/subscriptions").json()) == 2
    # a cancelled row does not count as a duplicate
    for row in a.get("/api/subscriptions").json():
        a.patch(f"/api/subscriptions/{row['id']}", json={"status": "cancelled"})
    assert a.post("/api/subscriptions", json=sub("Netflix", provider_id="netflix")).status_code == 200


# ---- 4/5/6. discovery candidates -------------------------------------------------------


def import_text():
    return statement(
        "Tarih;Açıklama;Tutar",  # header -> parsed as CSV
        *monthly_rows("NETFLIX.COM ISTANBUL", "229,99"),
        *monthly_rows("OPENAI *CHATGPT SUBSCR", "20.00 USD"),
        f"{finance.today().isoformat()};APPLE.COM/BILL;49,99 TL",
        f"{finance.today().isoformat()};MIGROS KADIKOY;512,40",  # not a subscription -> ignored
    )


def test_import_creates_candidates_but_never_subscriptions(clients):
    a, _ = clients
    r = a.post("/api/subscriptions/candidates/import", json={"text": import_text()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["skipped_lines"] == 0 and body["created"] == 3
    assert a.get("/api/subscriptions").json() == []  # candidates are not subscriptions
    assert a.get("/api/dashboard/summary").json()["subscription_monthly"] == 0
    by_name = {c["provider_name"]: c for c in body["candidates"]}
    netflix = by_name["Netflix"]
    assert (netflix["provider_id"], netflix["billing_cycle"], netflix["suggested_price"], netflix["status"]) == ("netflix", "monthly", 229.99, "pending")
    assert netflix["confidence_label"] == "high" and netflix["explanation"] == "İçe aktardığın hesap dökümünde tespit edildi"
    assert date.fromisoformat(netflix["renewal_date"]) >= finance.today()
    chatgpt = by_name["ChatGPT Plus"]
    assert chatgpt["alternatives"] == ["chatgpt-pro"] and chatgpt["currency"] == "USD"
    apple = next(c for c in body["candidates"] if c["ambiguous"])
    assert apple["provider_id"] is None and apple["confidence_label"] == "review"
    assert "icloud-plus" in apple["alternatives"]
    assert "MIGROS" not in r.text
    # privacy: raw descriptors (with location) are not stored, only the normalized merchant
    stored = db["subscription_candidates"].docs
    assert all("ISTANBUL" not in str(doc) for doc in stored)


def test_candidates_are_isolated_between_users(clients):
    a, b = clients
    a.post("/api/subscriptions/candidates/import", json={"text": import_text()})
    candidate = a.get("/api/subscriptions/candidates").json()[0]
    assert b.get("/api/subscriptions/candidates").json() == []
    assert b.post(f"/api/subscriptions/candidates/{candidate['id']}/accept", json={}).status_code == 404
    assert b.post(f"/api/subscriptions/candidates/{candidate['id']}/reject").status_code == 404
    assert b.get("/api/subscriptions").json() == []
    assert a.get("/api/subscriptions/candidates?status=pending").json()[0]["status"] == "pending"
    assert b.get("/api/subscriptions/discovery/status").json()["pending_candidates"] == 0
    assert candidate["provider_name"] not in b.get("/api/account/export").text


def test_only_owner_accept_turns_candidate_into_subscription(clients):
    a, _ = clients
    a.post("/api/subscriptions/candidates/import", json={"text": statement(*monthly_rows("NETFLIX", "229,99"))})
    candidate = a.get("/api/subscriptions/candidates").json()[0]
    r = a.post(f"/api/subscriptions/candidates/{candidate['id']}/accept", json={"plan": "Standart", "payment_method": "Banka kartı"})
    assert r.status_code == 200, r.text
    created = r.json()["subscription"]
    assert (created["source"], created["provider_id"], created["plan"], created["price"], created["candidate_id"]) == ("import", "netflix", "Standart", 229.99, candidate["id"])
    assert r.json()["candidate"]["status"] == "accepted"
    assert [s["id"] for s in a.get("/api/subscriptions").json()] == [created["id"]]
    assert a.post(f"/api/subscriptions/candidates/{candidate['id']}/accept", json={}).status_code == 409
    assert a.post(f"/api/subscriptions/candidates/{candidate['id']}/reject").status_code == 409


def test_accept_requires_price_and_valid_date_and_allowed_provider(clients):
    a, _ = clients
    a.post("/api/subscriptions/candidates/import", json={"text": f"{finance.today().isoformat()};APPLE.COM/BILL;49,99"})
    apple = a.get("/api/subscriptions/candidates").json()[0]
    assert apple["ambiguous"]
    assert a.post(f"/api/subscriptions/candidates/{apple['id']}/accept", json={"renewal_date": "2026-05-01"}).status_code == 422  # which service?
    assert a.post(f"/api/subscriptions/candidates/{apple['id']}/accept", json={"provider_id": "netflix", "renewal_date": "2026-05-01"}).status_code == 422
    assert a.post(f"/api/subscriptions/candidates/{apple['id']}/accept", json={"provider_id": "icloud-plus", "renewal_date": "2026-02-30"}).status_code == 422
    assert a.post(f"/api/subscriptions/candidates/{apple['id']}/accept", json={"provider_id": "icloud-plus"}).status_code == 422  # single payment: no renewal date known
    assert a.get("/api/subscriptions").json() == []
    ok = a.post(f"/api/subscriptions/candidates/{apple['id']}/accept", json={"provider_id": "icloud-plus", "renewal_date": "2026-05-01", "plan": "200 GB"})
    assert ok.status_code == 200 and ok.json()["subscription"]["name"] == "iCloud+"


def test_reject_is_final_and_not_resurfaced_by_reimport(clients):
    a, _ = clients
    text = statement(*monthly_rows("SPOTIFY P1234", "99,99"))
    a.post("/api/subscriptions/candidates/import", json={"text": text})
    candidate = a.get("/api/subscriptions/candidates").json()[0]
    assert a.post(f"/api/subscriptions/candidates/{candidate['id']}/reject").json()["status"] == "rejected"
    again = a.post("/api/subscriptions/candidates/import", json={"text": text}).json()
    assert (again["created"], again["skipped_rejected"]) == (0, 1)
    assert a.get("/api/subscriptions/candidates?status=pending").json() == []
    assert a.get("/api/subscriptions").json() == []


def test_reimport_merges_instead_of_duplicating(clients):
    a, _ = clients
    text = statement(*monthly_rows("NETFLIX", "229,99"))
    a.post("/api/subscriptions/candidates/import", json={"text": text})
    again = a.post("/api/subscriptions/candidates/import", json={"text": text}).json()
    assert (again["created"], again["merged"]) == (0, 1)
    assert len(a.get("/api/subscriptions/candidates").json()) == 1


def test_candidate_matching_existing_subscription_is_flagged_not_merged(clients):
    a, _ = clients
    existing = a.post("/api/subscriptions", json=sub("ChatGPT", price=20, currency="USD")).json()  # typed by hand, no provider id
    a.post("/api/subscriptions/candidates/import", json={"text": statement(*monthly_rows("OPENAI", "20 USD"))})
    candidate = a.get("/api/subscriptions/candidates").json()[0]
    assert [m["id"] for m in candidate["possible_duplicates"]] == [existing["id"]]
    conflict = a.post(f"/api/subscriptions/candidates/{candidate['id']}/accept", json={})
    assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "possible_duplicate"
    assert len(a.get("/api/subscriptions").json()) == 1  # nothing merged or added automatically
    assert a.post(f"/api/subscriptions/candidates/{candidate['id']}/accept", json={"confirm_duplicate": True}).status_code == 200
    assert len(a.get("/api/subscriptions").json()) == 2


def test_import_limits(clients):
    a, _ = clients
    assert a.post("/api/subscriptions/candidates/import", json={"text": "x\n" * 5001}).status_code == 413
    assert a.post("/api/subscriptions/candidates/import", json={"text": ""}).status_code == 422


# ---- 7. e-mail discovery (analysis only; no mailbox) ---------------------------------------


def test_email_sources_are_reported_honestly(clients):
    a, _ = clients
    status = a.get("/api/subscriptions/discovery/status").json()
    assert status["email"]["connected"] is False and status["email"]["available"] is False
    assert status["transaction"]["connected"] is False
    assert status["manual_import"]["available"] is True
    assert a.post("/api/subscriptions/discovery/email/gmail/connect").status_code == 501
    assert a.post("/api/subscriptions/discovery/email/unknown/connect").status_code == 404
    assert a.get("/api/subscriptions").json() == [] and a.get("/api/subscriptions/candidates").json() == []


def test_classify_email_signals_and_privacy():
    receipt = classify_email(EmailMessageMeta(sender="Netflix <info@mailer.netflix.com>", subject="Ödemeniz alındı - fatura #1234 kart 4821", received_at="2026-03-02T10:00:00Z", snippet="Merhaba Ada, ..."))
    assert receipt["provider_ids"] == ["netflix"] and receipt["signal"] == "payment_confirmation" and receipt["observed_at"] == "2026-03-02"
    assert "subject" not in receipt and "snippet" not in receipt and "4821" not in str(receipt)
    assert classify_email(EmailMessageMeta(sender="friend@gmail.com", subject="Netflix invoice", received_at="2026-03-02")) is None
    assert classify_email(EmailMessageMeta(sender="no-reply@spotify.com", subject="Hello there", received_at="2026-03-02")) is None
    assert classify_email(EmailMessageMeta(sender="no-reply@spotify.com", subject="Your subscription was cancelled", received_at="2026-03-02"))["signal"] == "cancelled"
    assert classify_email(EmailMessageMeta(sender="noreply@tm.openai.com", subject="Your ChatGPT Plus renewal", received_at="2026-03-02"))["signal"] == "renewal"


def test_cancelled_emails_do_not_become_candidates_and_apple_sender_is_ambiguous():
    cancelled = [{"provider_ids": ["spotify"], "signal": "cancelled", "sender_domain": "spotify.com", "observed_at": "2026-03-01"}]
    assert candidate_service.email_drafts(cancelled) == []
    apple = candidate_service.email_drafts([{"provider_ids": provider_catalog.match_sender("no_reply@email.apple.com"), "signal": "receipt", "sender_domain": "email.apple.com", "observed_at": "2026-03-01"}])[0]
    assert apple["ambiguous"] and apple["provider_id"] is None and apple["suggested_price"] is None


async def test_email_plus_transaction_evidence_merges_into_one_candidate():
    for collection in db.collections.values():
        collection.docs.clear()
    email = candidate_service.email_drafts([{"provider_ids": ["max"], "signal": "receipt", "sender_domain": "max.com", "observed_at": "2026-03-01"}])
    await candidate_service.upsert_candidates("user_x", email)
    txns = [Transaction(date=date(2026, 1, 1) + timedelta(days=30 * i), description="MAX.COM HELP", amount=199.9) for i in range(3)]
    tx_drafts = detect_recurring(txns, evidence_type="transaction", evidence_source="bank_feed", today=date(2026, 3, 5))
    result = await candidate_service.upsert_candidates("user_x", tx_drafts)
    assert (result["created"], result["merged"]) == (0, 1)
    [row] = await candidate_service.list_candidates("user_x")
    assert row["explanation"] == "E-posta + ödeme hareketi eşleşti"
    assert row["evidence_types"] == ["email", "transaction"] and row["confidence_label"] == "high"
    assert await candidate_service.list_candidates("someone_else") == []
    assert db.subscriptions.docs == []



# ---- 8. merchant normalization / recurrence -----------------------------------------


@pytest.mark.parametrize("descriptor, kind, first", [
    ("NETFLIX.COM", "provider", "netflix"), ("GOOGLE*YOUTUBE PREMIUM", "provider", "youtube-premium"), ("GOOGLE *GOOGLE ONE", "provider", "google-one"),
    ("GOOGLE *PLAY", "ambiguous", "google-one"), ("APPLE.COM/BILL ITUNES.COM", "ambiguous", "icloud-plus"), ("AMAZON MKTPLACE", "ambiguous", "amazon-prime"),
    ("MICROSOFT*STORE", "ambiguous", "microsoft-365"), ("AMAZON PRIME*TR", "provider", "amazon-prime"), ("OPENAI *CHATGPT", "provider", "chatgpt-plus"),
])
def test_merchant_normalization(descriptor, kind, first):
    match = provider_catalog.match_merchant(descriptor)
    assert match["kind"] == kind and match["provider_ids"][0] == first


def test_unknown_merchants_are_ignored_and_ambiguous_github_is_not_guessed():
    today = date(2026, 4, 1)
    drafts = detect_recurring([Transaction(date(2026, 1, 5), "BIM MARKET", 80), Transaction(date(2026, 2, 5), "GITHUB INC", 10), Transaction(date(2026, 3, 5), "GITHUB INC", 10)], evidence_type="manual_import", evidence_source="import", today=today)
    assert len(drafts) == 1 and drafts[0]["ambiguous"] and drafts[0]["provider_id"] is None
    assert set(drafts[0]["alternatives"]) == {"github", "github-copilot"}


def test_recurrence_detection_cycles():
    t = date(2026, 6, 1)
    yearly = detect_recurring([Transaction(date(2024, 5, 10), "ADOBE", 2400), Transaction(date(2025, 5, 10), "ADOBE", 2600)], evidence_type="manual_import", evidence_source="import", today=t)[0]
    assert yearly["billing_cycle"] == "yearly" and yearly["renewal_date"] == "2026-05-10" or yearly["renewal_date"] >= t.isoformat()
    irregular = detect_recurring([Transaction(date(2026, 1, 1), "SPOTIFY", 99), Transaction(date(2026, 1, 9), "SPOTIFY", 99)], evidence_type="manual_import", evidence_source="import", today=t)[0]
    assert irregular["billing_cycle"] is None and irregular["renewal_date"] is None and irregular["confidence"] < 0.75


def test_statement_parsing_formats():
    assert parse_amount("1.299,90") == 1299.9 and parse_amount("1,299.90") == 1299.9 and parse_amount("229,99") == 229.99 and parse_amount("-49.99") == -49.99 and parse_amount("1.299") == 1299
    txns, skipped = parse_statement("05.01.2026 NETFLIX.COM 229,99 TL\n2026-01-06\tSPOTIFY\t-99.99\n06/01/2026,DEEZER,$9.99\nbozuk satır\n2026-02-30;NETFLIX;1")
    assert [(t.date.isoformat(), t.description, t.amount, t.currency) for t in txns] == [("2026-01-05", "NETFLIX.COM", 229.99, "TRY"), ("2026-01-06", "SPOTIFY", 99.99, "TRY"), ("2026-01-06", "DEEZER", 9.99, "USD")]
    assert skipped == 2


# ---- 11/12. source badge & legacy rows -----------------------------------------------------


def test_legacy_rows_are_kept_labelled_and_reviewable(clients):
    a, b = clients
    uid = user_id(a)
    legacy = {"id": "legacy-1", "user_id": uid, "name": "Netflix", "category": "Eğlence", "price": 229.99, "currency": "TRY", "renewal_date": finance.today().isoformat(),
              "payment_method": "Kart •••• 4821", "cancellation_url": "https://www.netflix.com/cancelplan", "source": "manual", "status": "active", "billing_cycle": "monthly", "usage": "active", "created_at": "2025-01-01T00:00:00+00:00"}
    db.subscriptions.docs.append(dict(legacy))
    row = a.get("/api/subscriptions").json()[0]
    assert (row["source"], row["legacy"], row["legacy_reviewed"]) == ("legacy", True, False)  # not claimed as manual/email
    assert a.get("/api/subscriptions/insights").json()["legacy_unreviewed"] == 1
    assert b.post("/api/subscriptions/legacy-1/review").status_code == 404
    reviewed = a.post("/api/subscriptions/legacy-1/review").json()
    assert (reviewed["source"], reviewed["legacy_reviewed"], reviewed["price"], reviewed["name"]) == ("legacy", True, 229.99, "Netflix")
    assert a.get("/api/subscriptions/insights").json()["legacy_unreviewed"] == 0
    # a legacy "Netflix" row still counts as a possible duplicate of a new Netflix entry
    assert a.post("/api/subscriptions", json=sub("Netflix", provider_id="netflix")).status_code == 409
    assert len(a.get("/api/subscriptions").json()) == 1  # nothing deleted, nothing added


# ---- 10. insights & calculations ----------------------------------------------------------


def test_monthly_yearly_quarterly_math_and_status_filtering(clients):
    a, _ = clients
    today = finance.today()
    a.post("/api/subscriptions", json=sub("Netflix", provider_id="netflix", price=100))
    a.post("/api/subscriptions", json=sub("Adobe", provider_id="adobe-creative-cloud", price=1200, billing_cycle="yearly", renewal_date=(today + timedelta(days=200)).isoformat()))
    a.post("/api/subscriptions", json=sub("Exxen", provider_id="exxen", price=300, billing_cycle="quarterly", usage="unused"))
    cancelled = a.post("/api/subscriptions", json=sub("Spotify", provider_id="spotify", price=999)).json()
    a.patch(f"/api/subscriptions/{cancelled['id']}", json={"status": "cancelled"})
    ins = a.get("/api/subscriptions/insights").json()
    assert ins["active_count"] == 3 and ins["total_count"] == 4
    assert ins["monthly_total_try"] == 300 and ins["yearly_projection_try"] == 3600
    assert ins["unused_count"] == 1 and ins["unused_monthly_try"] == 100
    assert {y["name"]: y["monthly_equivalent_try"] for y in ins["yearly_subscriptions"]} == {"Adobe": 100, "Exxen": 100}
    upcoming = [u["name"] for u in ins["upcoming"]]
    assert "Spotify" not in upcoming and "Adobe" not in upcoming and set(upcoming) == {"Netflix", "Exxen"}
    assert ins["next_renewal"]["date"] == today.isoformat()
    summary = a.get("/api/dashboard/summary").json()
    assert summary["subscription_monthly"] == 300 and "Spotify" not in [u["title"] for u in summary["upcoming"]]
    usd = a.post("/api/subscriptions", json=sub("ChatGPT", provider_id="chatgpt-plus", price=20, currency="USD")).json()
    assert a.get("/api/subscriptions/insights").json()["monthly_total_try"] == 300 + 20 * finance.RATES["USD"]
    assert usd["currency"] == "USD"


def test_quarterly_renewal_projection():
    anchor = date(2026, 1, 31)
    subscription = {"renewal_date": anchor.isoformat(), "billing_cycle": "quarterly", "price": 90, "currency": "TRY"}
    assert finance.sub_next_renewal(subscription, date(2026, 2, 1)) == date(2026, 4, 30)
    assert finance.sub_monthly(subscription) == 30


def test_paid_bills_are_not_upcoming_and_unpaid_ones_are():
    tomorrow = finance.today() + timedelta(days=1)
    data = {"subscriptions": [], "bills": [
        {"id": "paid", "provider": "Power", "amount": 10, "bill_type": "Elektrik", "status": "paid", "frequency": "monthly", "due_date": tomorrow.isoformat()},
        {"id": "open", "provider": "Water", "amount": 10, "bill_type": "Su", "status": "pending", "frequency": "once", "due_date": tomorrow.isoformat()},
    ]}
    upcoming = finance.upcoming_payments(data, finance.today())
    assert [(u["id"], u["date"]) for u in upcoming if u["date"] == tomorrow.isoformat()] == [("open", tomorrow.isoformat())]


def test_price_change_history_and_overlap_insight(clients):
    a, _ = clients
    netflix = a.post("/api/subscriptions", json=sub("Netflix", provider_id="netflix", price=199.99)).json()
    a.post("/api/subscriptions", json=sub("Prime Video", provider_id="prime-video", price=39.9))
    a.post("/api/subscriptions", json=sub("BluTV", price=99.9))  # typed by hand; catalog alias of Max
    updated = a.patch(f"/api/subscriptions/{netflix['id']}", json={"price": 229.99}).json()
    assert [h["price"] for h in updated["price_history"]] == [199.99]
    a.patch(f"/api/subscriptions/{netflix['id']}", json={"usage": "rarely"})  # no price change -> no new history row
    ins = a.get("/api/subscriptions/insights").json()
    assert ins["price_changes"][0]["previous_price"] == 199.99 and ins["price_changes"][0]["change_percent"] == 15.0
    overlap = next(o for o in ins["overlaps"] if o["category"] == "streaming")
    assert overlap["count"] == 3 and overlap["message"].startswith("3 video yayın aboneliğin bulunuyor")


# ---- account lifecycle ------------------------------------------------------------------------


def test_export_and_delete_cover_candidates_for_owner_only(clients):
    a, b = clients
    a.post("/api/subscriptions/candidates/import", json={"text": statement(*monthly_rows("NETFLIX", "229,99"))})
    b.post("/api/subscriptions/candidates/import", json={"text": statement(*monthly_rows("SPOTIFY", "99,99"))})
    export = a.get("/api/account/export").json()
    assert [c["provider_id"] for c in export["subscription_candidates"]] == ["netflix"]
    assert a.delete("/api/account").status_code == 204
    assert [d["provider_id"] for d in db["subscription_candidates"].docs] == ["spotify"]
