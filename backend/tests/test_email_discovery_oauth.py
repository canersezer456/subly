"""Mailbox (Gmail / Outlook) OAuth + metadata sync, end to end through the real routers.

Google/Microsoft endpoints are replaced by an httpx.MockTransport — no network, no real
credentials. Client ids/secrets below are dummy strings; the Fernet key is generated
per test run. What is verified: honest not-configured behaviour, PKCE/state handling,
per-user ownership of the flow, encrypted token storage, metadata-only reads, and that
a sync only ever creates *pending candidates*.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from isolated_store import create_app
from lib import finance, provider_catalog
from lib.db import db
from lib.discovery import mailbox, token_crypto
from lib.discovery.email_source import EmailMessageMeta, classify_email

REFRESH = "rt-plaintext-refresh-token-value"
ACCESS = "at-plaintext-access-token-value"
GMAIL_ENV = {"GMAIL_OAUTH_CLIENT_ID": "dummy-client-id", "GMAIL_OAUTH_CLIENT_SECRET": "dummy-client-secret", "GMAIL_OAUTH_REDIRECT_URI": "https://app.example/api/subscriptions/discovery/email/gmail/callback"}
OUTLOOK_ENV = {"OUTLOOK_OAUTH_CLIENT_ID": "dummy-ms-id", "OUTLOOK_OAUTH_CLIENT_SECRET": "dummy-ms-secret", "OUTLOOK_OAUTH_REDIRECT_URI": "https://app.example/api/subscriptions/discovery/email/outlook/callback"}


@pytest.fixture
def clients():
    for collection in db.collections.values():
        collection.docs.clear()
    app = create_app()
    with TestClient(app, base_url="https://testserver") as a, TestClient(app, base_url="https://testserver") as b:
        for client, name in ((a, "alpha"), (b, "beta")):
            assert client.post("/api/auth/register", json={"email": f"{name}@example.com", "name": name, "password": "TestPass123!"}).status_code == 200
        yield a, b


@pytest.fixture
def configured(monkeypatch):
    for key, value in {**GMAIL_ENV, **OUTLOOK_ENV}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv(token_crypto.KEY_ENV, Fernet.generate_key().decode())


class FakeProviders:
    """Stands in for accounts.google.com / oauth2.googleapis.com / gmail / Microsoft."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.token_scope = "https://www.googleapis.com/auth/gmail.metadata"
        self.refresh_status = 200
        self.responses: dict[str, httpx.Response] = {}
        self.gmail_messages: list[dict] = []
        self.outlook_pages: list[list[dict]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url.startswith("https://oauth2.googleapis.com/token") or "/oauth2/v2.0/token" in url:
            form = parse_qs(request.content.decode())
            if form["grant_type"] == ["authorization_code"]:
                assert form["code_verifier"][0]  # PKCE verifier is sent
                return httpx.Response(200, json={"access_token": ACCESS, "refresh_token": REFRESH, "scope": self.token_scope, "expires_in": 3600})
            if "refresh" in self.responses:
                value = self.responses["refresh"]
                return value.pop(0) if isinstance(value, list) else value
            if self.refresh_status != 200:
                return httpx.Response(self.refresh_status, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": ACCESS, "expires_in": 3600})
        if url.startswith("https://oauth2.googleapis.com/revoke"):
            return httpx.Response(200)
        if url.startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages/"):
            message_id = request.url.path.rsplit("/", 1)[-1]
            if message_id in self.responses:
                value = self.responses[message_id]
                return value.pop(0) if isinstance(value, list) else value
            msg = next(m for m in self.gmail_messages if m["id"] == message_id)
            return httpx.Response(200, json={"id": message_id, "internalDate": str(msg["ts"]), "payload": {"headers": [{"name": "From", "value": msg["from"]}, {"name": "Subject", "value": msg["subject"]}]}})
        if url.startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages"):
            if "list" in self.responses:
                value = self.responses["list"]
                return value.pop(0) if isinstance(value, list) else value
            return httpx.Response(200, json={"messages": [{"id": m["id"]} for m in self.gmail_messages]})
        if url.startswith("https://graph.microsoft.com/v1.0/me/messages"):
            page = int(request.url.params.get("page", "0"))
            body = {"value": self.outlook_pages[page]}
            if page + 1 < len(self.outlook_pages):
                body["@odata.nextLink"] = f"https://graph.microsoft.com/v1.0/me/messages?page={page + 1}"
            return httpx.Response(200, json=body)
        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch):
    async def no_pause(attempt, *args):
        pass
    monkeypatch.setattr(mailbox, "_retry_pause", no_pause)
    providers = FakeProviders()
    monkeypatch.setattr(mailbox, "http_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(providers.handler)))
    return providers


def ms(days_ago: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp() * 1000)


def connect(client, provider="gmail") -> str:
    r = client.post(f"/api/subscriptions/discovery/email/{provider}/connect")
    assert r.status_code == 200, r.text
    return parse_qs(urlparse(r.json()["authorization_url"]).query)["state"][0]


def callback(client, provider="gmail", **params):
    return client.get(f"/api/subscriptions/discovery/email/{provider}/callback", params=params, follow_redirects=False)


def redirect_params(response) -> dict:
    assert response.status_code == 303
    location = urlparse(response.headers["location"])
    assert location.path == "/subscriptions"
    return {k: v[0] for k, v in parse_qs(location.query).items()}


# ---- not configured: honest refusal ------------------------------------------------------


def test_without_oauth_config_nothing_connects_or_reads(clients, fake):
    a, _ = clients
    status = a.get("/api/subscriptions/discovery/status").json()["email"]
    assert status["state"] == "not_configured" and status["connected"] is False
    assert {x["state"] for x in status["adapters"]} == {"not_configured"}
    for provider in ("gmail", "outlook"):
        assert a.post(f"/api/subscriptions/discovery/email/{provider}/connect").status_code == 501
        assert a.post(f"/api/subscriptions/discovery/email/{provider}/sync").status_code == 501
    assert fake.requests == []  # no call ever left the server
    assert a.get("/api/subscriptions/candidates").json() == [] and a.get("/api/subscriptions").json() == []


def test_missing_encryption_key_blocks_connection(clients, fake, monkeypatch):
    for key, value in GMAIL_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(token_crypto.KEY_ENV, raising=False)
    assert "EMAIL_TOKEN_ENCRYPTION_KEY" in mailbox.GMAIL.missing_config()
    assert clients[0].post("/api/subscriptions/discovery/email/gmail/connect").status_code == 501
    monkeypatch.setenv(token_crypto.KEY_ENV, "not-a-fernet-key")
    assert clients[0].post("/api/subscriptions/discovery/email/gmail/connect").status_code == 501


# ---- consent URL ----------------------------------------------------------------------------


def test_connect_builds_minimal_scope_pkce_consent_url(clients, configured, fake):
    a, _ = clients
    assert a.get("/api/subscriptions/discovery/status").json()["email"]["adapters"][0]["state"] == "available"
    url = urlparse(a.post("/api/subscriptions/discovery/email/gmail/connect").json()["authorization_url"])
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert url.netloc == "accounts.google.com"
    assert q["scope"] == "https://www.googleapis.com/auth/gmail.metadata"  # headers only, no bodies
    assert q["code_challenge_method"] == "S256" and len(q["code_challenge"]) >= 43
    assert q["access_type"] == "offline" and q["include_granted_scopes"] == "false"
    assert q["redirect_uri"] == GMAIL_ENV["GMAIL_OAUTH_REDIRECT_URI"] and "client_secret" not in q
    ms_url = urlparse(a.post("/api/subscriptions/discovery/email/outlook/connect").json()["authorization_url"])
    assert ms_url.netloc == "login.microsoftonline.com"
    assert parse_qs(ms_url.query)["scope"][0] == "offline_access https://graph.microsoft.com/Mail.ReadBasic"
    assert fake.requests == []  # building the URL contacts nobody


# ---- callback -----------------------------------------------------------------------------------


def test_callback_stores_only_an_encrypted_refresh_token(clients, configured, fake, caplog):
    a, _ = clients
    caplog.set_level(logging.DEBUG)
    state = connect(a)
    params = redirect_params(callback(a, code="auth-code-123", state=state))
    assert params == {"tab": "discover", "email": "connected", "provider": "gmail"}
    [conn] = db[mailbox.CONNECTIONS].docs
    assert conn["status"] == "connected" and conn["refresh_token_enc"] != REFRESH
    assert token_crypto.decrypt(conn["refresh_token_enc"]) == REFRESH
    dumped = json.dumps(db[mailbox.CONNECTIONS].docs + db[mailbox.STATES].docs, default=str)
    assert REFRESH not in dumped and ACCESS not in dumped  # no plaintext token, access token never stored
    assert REFRESH not in caplog.text and ACCESS not in caplog.text and "auth-code-123" not in caplog.text
    status = a.get("/api/subscriptions/discovery/status")
    assert REFRESH not in status.text and "refresh_token" not in status.text
    assert status.json()["email"]["adapters"][0]["state"] == "connected"
    # the state is single use
    assert redirect_params(callback(a, code="auth-code-123", state=state))["reason"] == "state_invalid"


def test_state_is_bound_to_the_user_who_started_the_flow(clients, configured, fake):
    a, b = clients
    state = connect(a)
    params = redirect_params(callback(b, code="stolen", state=state))  # B's browser, A's state
    assert params["email"] == "error" and params["reason"] == "state_invalid"
    assert db[mailbox.CONNECTIONS].docs == []
    assert redirect_params(callback(a, code="late", state=state))["reason"] == "state_invalid"  # consumed
    assert not any("oauth2.googleapis.com/token" in str(r.url) for r in fake.requests)


def test_callback_rejections(clients, configured, fake):
    a, _ = clients
    assert redirect_params(callback(a, error="access_denied", state=connect(a)))["reason"] == "denied"
    fake.token_scope = "openid email"  # user unticked the mailbox permission
    assert redirect_params(callback(a, code="c", state=connect(a)))["reason"] == "scope_missing"
    fake.token_scope = "https://www.googleapis.com/auth/gmail.metadata"
    state = connect(a)
    db[mailbox.STATES].docs[0]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert redirect_params(callback(a, code="c", state=state))["reason"] == "state_expired"
    assert redirect_params(callback(a, code="c", state="forged"))["reason"] == "state_invalid"
    assert db[mailbox.CONNECTIONS].docs == []
    anonymous = TestClient(create_app(), base_url="https://testserver")
    assert redirect_params(anonymous.get("/api/subscriptions/discovery/email/gmail/callback", params={"code": "c", "state": "s"}, follow_redirects=False))["reason"] == "session"


# ---- sync ------------------------------------------------------------------------------------------


def gmail_inbox():
    return [
        {"id": "m1", "ts": ms(3), "from": "Netflix <info@mailer.netflix.com>", "subject": "Ödemeniz alındı"},
        {"id": "m2", "ts": ms(5), "from": "siparis@amazon.com.tr", "subject": "Siparişiniz onaylandı - order confirmation #123"},  # shopping: not Prime
        {"id": "m3", "ts": ms(6), "from": "prime@amazon.com.tr", "subject": "Prime üyeliğiniz yenilendi"},
        {"id": "m4", "ts": ms(7), "from": "no_reply@email.apple.com", "subject": "Apple'dan faturanız"},  # which Apple service?
        {"id": "m5", "ts": ms(8), "from": "news@spotify.com", "subject": "Your subscription was cancelled"},  # ended: not proposed
        {"id": "m6", "ts": ms(9), "from": "friend@gmail.com", "subject": "Netflix invoice joke"},
        {"id": "m7", "ts": ms(9), "from": "noreply@tm.openai.com", "subject": "Your ChatGPT Plus subscription has renewed"},
        {"id": "m8", "ts": ms(600), "from": "info@mailer.netflix.com", "subject": "Ödemeniz alındı"},  # older than lookback
    ]


def test_gmail_sync_reads_headers_only_and_creates_pending_candidates_only(clients, configured, fake):
    a, b = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scanned"] == 7 and body["created"] == 4
    by_name = {c["provider_name"]: c for c in body["candidates"]}
    assert set(by_name) == {"Netflix", "Amazon Prime", "ChatGPT Plus", "Apple TV+ / Apple Music / iCloud+ / Apple One"}
    assert all(c["status"] == "pending" for c in body["candidates"])
    assert by_name["Netflix"]["explanation"] == "E-posta faturasında tespit edildi"
    assert by_name["Netflix"]["suggested_price"] is None  # prices are never read from mail
    apple = by_name["Apple TV+ / Apple Music / iCloud+ / Apple One"]
    assert apple["ambiguous"] and apple["provider_id"] is None and apple["confidence_label"] == "review"
    assert by_name["ChatGPT Plus"]["alternatives"] == ["chatgpt-pro"]
    # nothing owned was created, nothing leaked to B
    assert a.get("/api/subscriptions").json() == [] and b.get("/api/subscriptions/candidates").json() == []
    # metadata-only requests, bearer auth, no subject text persisted
    gets = [r for r in fake.requests if "gmail.googleapis.com" in str(r.url) and "/messages/" in str(r.url)]
    assert gets and all(r.url.params.get("format") == "metadata" for r in gets)
    assert all(r.url.params.get("fields") == "internalDate,payload/headers" for r in gets)
    assert all(r.url.params.get_list("metadataHeaders") == ["From", "Subject"] for r in gets)
    assert all("q" not in r.url.params for r in fake.requests)
    assert body["partial"] is False and body["skipped"] == 0
    assert all(r.headers["authorization"] == f"Bearer {ACCESS}" for r in gets)
    stored = json.dumps(db["subscription_candidates"].docs, ensure_ascii=False)
    assert "Ödemeniz" not in stored and "faturanız" not in stored and "renewed" not in stored
    last = a.get("/api/subscriptions/discovery/status").json()["email"]["adapters"][0]
    assert last["last_sync"]["created"] == 4 and last["last_sync_at"]


def test_candidate_from_email_becomes_subscription_only_on_owner_accept(clients, configured, fake):
    a, b = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()
    netflix = next(c for c in a.post("/api/subscriptions/discovery/email/gmail/sync").json()["candidates"] if c["provider_id"] == "netflix")
    assert b.post(f"/api/subscriptions/candidates/{netflix['id']}/accept", json={"price": 229.99, "renewal_date": finance.today().isoformat()}).status_code == 404
    assert a.post(f"/api/subscriptions/candidates/{netflix['id']}/accept", json={}).status_code == 422  # no price from mail: user must enter it
    ok = a.post(f"/api/subscriptions/candidates/{netflix['id']}/accept", json={"price": 229.99, "renewal_date": finance.today().isoformat()})
    assert ok.status_code == 200 and ok.json()["subscription"]["source"] == "email"
    assert [s["name"] for s in a.get("/api/subscriptions").json()] == ["Netflix"] and b.get("/api/subscriptions").json() == []
    # a second sync does not recreate an accepted candidate
    again = a.post("/api/subscriptions/discovery/email/gmail/sync").json()
    assert again["created"] == 0 and again["already_accepted"] == 1


def test_outlook_sync_follows_paging_and_accepts_full_uri_scope(clients, configured, fake):
    a, _ = clients
    fake.token_scope = "https://graph.microsoft.com/Mail.ReadBasic offline_access"
    assert redirect_params(callback(a, "outlook", code="c", state=connect(a, "outlook")))["email"] == "connected"
    fake.outlook_pages = [
        [{"from": {"emailAddress": {"address": "no-reply@spotify.com"}}, "subject": "Your receipt", "receivedDateTime": "2026-03-01T10:00:00Z"}],
        [{"from": {"emailAddress": {"address": "noreply@disneyplus.com"}}, "subject": "Aboneliğiniz yenilendi", "receivedDateTime": "2026-03-02T10:00:00Z"}],
    ]
    body = a.post("/api/subscriptions/discovery/email/outlook/sync").json()
    assert body["scanned"] == 2 and {c["provider_id"] for c in body["candidates"]} == {"spotify", "disney-plus"}
    graph = [r for r in fake.requests if "graph.microsoft.com" in str(r.url)]
    assert graph[0].url.params["$select"] == "from,subject,receivedDateTime"  # never body
    assert all(c["evidence"][0]["source"] == "outlook" for c in body["candidates"])


def test_revoked_grant_requires_reconnect_and_creates_nothing(clients, configured, fake):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.refresh_status = 400
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "reauth_required"
    assert a.get("/api/subscriptions/discovery/status").json()["email"]["adapters"][0]["state"] == "reauth_required"
    assert a.get("/api/subscriptions/candidates").json() == []


def test_connections_are_private_and_disconnect_revokes(clients, configured, fake):
    a, b = clients
    callback(a, code="c", state=connect(a))
    assert b.get("/api/subscriptions/discovery/status").json()["email"]["connected"] is False
    assert b.post("/api/subscriptions/discovery/email/gmail/sync").status_code == 404
    assert b.delete("/api/subscriptions/discovery/email/gmail").status_code == 404
    assert len(db[mailbox.CONNECTIONS].docs) == 1
    export = a.get("/api/account/export").json()
    assert export["email_connections"][0]["provider"] == "gmail" and "refresh_token_enc" not in export["email_connections"][0]
    assert a.delete("/api/subscriptions/discovery/email/gmail").status_code == 204
    revoke = [r for r in fake.requests if str(r.url).startswith("https://oauth2.googleapis.com/revoke")]
    assert len(revoke) == 1 and db[mailbox.CONNECTIONS].docs == []


def test_account_deletion_removes_mailbox_grant(clients, configured, fake):
    a, b = clients
    callback(a, code="c", state=connect(a))
    callback(b, code="c", state=connect(b))
    assert a.delete("/api/account").status_code == 204
    assert [c["user_id"] for c in db[mailbox.CONNECTIONS].docs] == [b.get("/api/auth/me").json()["user_id"]]


# ---- structured Google failures / bounded metadata sync -------------------------------------------


def google_failure(status, reason=None):
    return httpx.Response(status, json={"error": {"message": "unsafe-provider-message", "errors": [{"reason": reason}]}})


@pytest.mark.parametrize("operation", ["list", "m1"])
@pytest.mark.parametrize("status,reason,code,http_status,reauth", [
    (401, None, "reauth_required", 409, True),
    (403, "insufficientPermissions", "scope_missing", 409, True),
    (403, "ACCESS_TOKEN_SCOPE_INSUFFICIENT", "scope_missing", 409, True),
    (403, "accessNotConfigured", "provider_configuration", 503, False),
    (403, "SERVICE_DISABLED", "provider_configuration", 503, False),
    (403, "domainPolicy", "provider_policy", 403, False),
    (403, "dailyLimitExceeded", "provider_quota", 429, False),
    (403, "unexpected", "provider_forbidden", 403, False),
    (403, None, "provider_forbidden", 403, False),
])
def test_google_failures_are_classified_without_assuming_reauth(clients, configured, fake, operation, status, reason, code, http_status, reauth):
    a, b = clients
    callback(a, code="c", state=connect(a))
    callback(b, code="c", state=connect(b))
    fake.gmail_messages = gmail_inbox()[:3]
    fake.responses[operation] = google_failure(status, reason)
    response = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert response.status_code == http_status
    assert response.json()["detail"]["code"] == code
    assert "unsafe-provider-message" not in response.text
    states = [c["status"] for c in db[mailbox.CONNECTIONS].docs]
    assert states == ["reauth_required" if reauth else "connected", "connected"]
    assert all(c["last_sync_at"] is None for c in db[mailbox.CONNECTIONS].docs)
    assert db["subscription_candidates"].docs == [] and db["subscriptions"].docs == []
    assert b.get("/api/subscriptions/candidates").json() == []


@pytest.mark.parametrize("body,status,code,http_status", [
    ({"error": "invalid_grant"}, 400, "reauth_required", 409),
    ({"error": "invalid_client"}, 401, "provider_configuration", 503),
    ({"error": "invalid_scope"}, 400, "scope_missing", 409),
    ({"error": "unknown"}, 400, "provider_unavailable", 502),
    ({"error": "unknown"}, 401, "provider_unavailable", 502),
    ({"access_token": ACCESS, "scope": "openid email"}, 200, "scope_missing", 409),
    ({"access_token": []}, 200, "provider_unavailable", 502),
])
def test_refresh_errors_do_not_all_invalidate_grants(clients, configured, fake, body, status, code, http_status):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.responses["refresh"] = httpx.Response(status, json=body)
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == http_status and r.json()["detail"]["code"] == code
    assert db[mailbox.CONNECTIONS].docs[0]["status"] == ("reauth_required" if code in ("reauth_required", "scope_missing") else "connected")
    assert not any("gmail.googleapis.com" in str(r.url) for r in fake.requests)


@pytest.mark.parametrize("operation", ["refresh", "list", "m1"])
@pytest.mark.parametrize("status,reason", [(429, None), (403, "userRateLimitExceeded"), (500, None), (503, None)])
def test_transient_google_errors_retry_and_recover(clients, configured, fake, operation, status, reason):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()[:1]
    success = {
        "refresh": {"access_token": ACCESS, "scope": mailbox.GMAIL.required_scope},
        "list": {"messages": [{"id": "m1"}]},
        "m1": {"internalDate": str(ms(3)), "payload": {"headers": [{"name": "From", "value": "info@netflix.com"}, {"name": "Subject", "value": "Your receipt"}]}},
    }
    fake.responses[operation] = [google_failure(status, reason), google_failure(status, reason), httpx.Response(200, json=success[operation])]
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 200, r.text
    assert r.json()["scanned"] == 1 and r.json()["partial"] is False
    assert fake.responses[operation] == []
    assert db[mailbox.CONNECTIONS].docs[0]["status"] == "connected"


@pytest.mark.parametrize("status,reason", [(429, None), (403, "rateLimitExceeded"), (503, None), (404, None)])
def test_exhausted_metadata_reports_partial_not_false_complete(clients, configured, fake, status, reason):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()[:3]
    fake.responses["m1"] = google_failure(status, reason)
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 200, r.text
    assert r.json()["partial"] is True and r.json()["skipped"] == 1 and r.json()["scanned"] == 2
    assert sum(req.url.path.endswith("/m1") for req in fake.requests) == (1 if status == 404 else 3)
    summary = a.get("/api/subscriptions/discovery/status").json()["email"]["adapters"][0]["last_sync"]
    assert summary["partial"] is True and summary["skipped"] == 1
    assert a.get("/api/subscriptions").json() == []


def test_partial_sync_preserves_candidates_and_keeps_connected(clients, configured, fake):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    # 3 messages: m1 (netflix), m2 (spotify), m3 (deezer)
    fake.gmail_messages = [
        {"id": "m1", "from": "info@mailer.netflix.com", "subject": "Faturanız", "ts": ms(1)},
        {"id": "m2", "from": "no-reply@spotify.com", "subject": "Your subscription renewed", "ts": ms(2)},
        {"id": "m3", "from": "billing@chatgpt.com", "subject": "ChatGPT receipt", "ts": ms(3)},
    ]
    # m2 encounters repeated RATE_LIMIT_EXCEEDED (403)
    fake.responses["m2"] = google_failure(403, "RATE_LIMIT_EXCEEDED")
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["partial"] is True
    assert body["skipped"] == 1
    assert body["scanned"] == 2
    assert body["created"] >= 1
    assert len(body["candidates"]) >= 1
    # Check that candidates are preserved in DB and not wiped
    candidates = a.get("/api/subscriptions/candidates").json()
    assert len(candidates) >= 1
    # Check that connection remains connected and not reauth_required
    status_resp = a.get("/api/subscriptions/discovery/status").json()
    gmail_adapter = next(ad for ad in status_resp["email"]["adapters"] if ad["id"] == "gmail")
    assert gmail_adapter["connected"] is True
    assert gmail_adapter["state"] == "connected"
    assert gmail_adapter["last_sync"]["partial"] is True
    assert gmail_adapter["last_sync"]["skipped"] == 1


@pytest.mark.parametrize("operation", ["refresh", "list", "m1"])
@pytest.mark.parametrize("status,code,http_status", [(429, "provider_quota", 429), (503, "provider_unavailable", 502)])
def test_all_failures_never_record_success(clients, configured, fake, operation, status, code, http_status):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()[:1]
    fake.responses[operation] = google_failure(status)
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == http_status and r.json()["detail"]["code"] == code
    assert db[mailbox.CONNECTIONS].docs[0]["last_sync_at"] is None
    assert db[mailbox.CONNECTIONS].docs[0]["status"] == "connected"
    assert db["subscription_candidates"].docs == []


@pytest.mark.parametrize("operation,payload", [
    ("refresh", []), ("refresh", "not-json"), ("list", []), ("list", "not-json"),
    ("list", {"messages": None}), ("list", {"messages": [{}]}),
    ("list", {"messages": [{"id": "../../anything"}]}),
    ("list", {"nextPageToken": []}), ("m1", "not-json"), ("m1", {}),
    ("m1", {"internalDate": "nan", "payload": {"headers": []}}),
    ("m1", {"internalDate": str(ms(1)), "payload": {"headers": [None]}}),
    ("m1", {"internalDate": "99999999999999999999999999", "payload": {"headers": []}}),
])
def test_malformed_google_responses_are_safe_failures(clients, configured, fake, operation, payload):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()[:1]
    fake.responses[operation] = httpx.Response(200, text=payload) if isinstance(payload, str) else httpx.Response(200, json=payload)
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 502 and r.json()["detail"]["code"] == "provider_unavailable"
    assert db[mailbox.CONNECTIONS].docs[0]["last_sync_at"] is None
    assert db["subscription_candidates"].docs == []


def test_duplicate_ids_are_fetched_once_and_page_cycles_fail(clients, configured, fake):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()[:1]
    fake.responses["list"] = [
        httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m1"}], "nextPageToken": "next"}),
        httpx.Response(200, json={"messages": [{"id": "m1"}]}),
    ]
    r = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert r.status_code == 200 and r.json()["scanned"] == 1
    assert sum(req.url.path.endswith("/m1") for req in fake.requests) == 1
    previous_sync = db[mailbox.CONNECTIONS].docs[0]["last_sync_at"]
    fake.responses["list"] = httpx.Response(200, json={"messages": [], "nextPageToken": "cycle"})
    assert a.post("/api/subscriptions/discovery/email/gmail/sync").status_code == 502
    assert db[mailbox.CONNECTIONS].docs[0]["last_sync_at"] == previous_sync


def test_missing_message_does_not_make_all_failed_sync_successful(clients, configured, fake):
    a, _ = clients
    callback(a, code="c", state=connect(a))
    fake.gmail_messages = gmail_inbox()[:1]
    fake.responses["m1"] = httpx.Response(404)
    assert a.post("/api/subscriptions/discovery/email/gmail/sync").status_code == 502
    assert db[mailbox.CONNECTIONS].docs[0]["last_sync_at"] is None


def test_mixed_auth_and_rate_reasons_never_skip_auth():
    response = httpx.Response(403, json={"error": {"errors": [{"reason": "rateLimitExceeded"}, {"reason": "insufficientPermissions"}]}})
    error = mailbox._google_error(response, "metadata")
    assert error.code == "scope_missing" and error.retryable is False


@pytest.mark.parametrize("response", [httpx.Response(403, text="not-json"), httpx.Response(403, json=[]), httpx.Response(403, json={"error": {"errors": [None, {"reason": []}], "details": "malformed"}})])
def test_unknown_malformed_403_is_not_auth_or_safe_to_skip(response):
    error = mailbox._google_error(response, "list")
    assert error.code == "provider_forbidden" and error.retryable is False


@pytest.mark.asyncio
async def test_metadata_concurrency_and_unique_fetch_budget():
    active = maximum = calls = 0

    async def handler(request):
        nonlocal active, maximum, calls
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": f"m{i}"} for i in range(30)]})
        calls += 1
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return httpx.Response(200, json={"internalDate": str(ms(1)), "payload": {"headers": []}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await mailbox._gmail_messages(client, ACCESS, finance.today() - timedelta(days=10), 12)
    assert calls == 12 and maximum <= 2
    assert len(result.messages) == 12 and result.skipped == 0


@pytest.mark.asyncio
async def test_retry_after_header_is_honored(monkeypatch):
    pauses = []
    calls = 0

    async def pause(attempt, retry_after=None):
        pauses.append((attempt, retry_after))

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "3"}, json={"error": {"errors": [{"reason": "rateLimitExceeded"}]}})
        return httpx.Response(200, json={"messages": []})

    monkeypatch.setattr(mailbox, "_retry_pause", pause)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resp = await mailbox._google_request(client, "GET", "https://gmail.googleapis.com/gmail/v1/users/me/messages", "list")
    assert resp.status_code == 200
    assert calls == 2
    assert pauses == [(0, 3.0)]


@pytest.mark.asyncio
async def test_transport_errors_retry_without_leaking_exception_text(monkeypatch, caplog):
    pauses = []
    calls = 0

    async def pause(attempt, *args):
        pauses.append(attempt)

    def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("exception-secret-canary", request=request)

    monkeypatch.setattr(mailbox, "_retry_pause", pause)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(mailbox.MailboxError) as caught:
            await mailbox._google_request(client, "GET", "https://gmail.googleapis.com/gmail/v1/users/me/messages", "list")
    assert calls == 3 and pauses == [0, 1]
    assert str(caught.value) == "provider_unavailable"
    assert "exception-secret-canary" not in caplog.text


def test_diagnostic_logs_only_allowlisted_structured_values(clients, configured, fake, caplog):
    a, _ = clients
    caplog.set_level(logging.DEBUG)
    state = connect(a)
    callback(a, code="auth-code-canary", state=state)
    canaries = ["raw-message-canary", "raw-domain-canary", "raw-metadata-canary", "raw-header-canary", "raw-url-canary", "unknown-reason-canary"]
    fake.responses["list"] = httpx.Response(403, headers={"X-Secret": canaries[3]}, json={"error": {
        "message": canaries[0], "errors": [{"reason": canaries[5], "location": canaries[4]}],
        "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "SERVICE_DISABLED", "domain": canaries[1], "metadata": {"secret": canaries[2]}}],
    }})
    response = a.post("/api/subscriptions/discovery/email/gmail/sync")
    assert response.status_code == 503
    diagnostics = [record.getMessage() for record in caplog.records if record.name == mailbox.__name__]
    assert diagnostics == ["mailbox provider=gmail operation=list status=403 reason=SERVICE_DISABLED"]
    for canary in [*canaries, REFRESH, ACCESS, GMAIL_ENV["GMAIL_OAUTH_CLIENT_SECRET"], "auth-code-canary", state]:
        assert canary not in caplog.text and canary not in response.text


# ---- sender / subject rules -----------------------------------------------------------------------


@pytest.mark.parametrize("sender, subject, expected", [
    ("info@mailer.netflix.com", "Faturanız", ["netflix"]),
    ("noreply@tm.openai.com", "Your receipt", ["chatgpt-plus", "chatgpt-pro"]),
    ("invoice+statements@mail.anthropic.com", "Your receipt from Anthropic", ["claude-pro", "claude-max"]),
    ("payments-noreply@google.com", "Google One aboneliğiniz yenilendi", ["google-one"]),
    ("payments-noreply@google.com", "Gemini Advanced receipt", ["google-gemini"]),
    ("payments-noreply@google.com", "YouTube Premium receipt", ["youtube-premium"]),
    ("payments-noreply@google.com", "Güvenlik uyarısı", []),
    ("no-reply@amazon.com.tr", "Prime üyelik yenileme", ["amazon-prime"]),
    ("no-reply@amazon.com.tr", "Siparişiniz kargoya verildi", []),
    ("no_reply@email.apple.com", "Your iCloud+ subscription", ["icloud-plus"]),
    ("no_reply@email.apple.com", "Your receipt from Apple", ["apple-tv-plus", "apple-music", "icloud-plus", "apple-one"]),
    ("reply@email.playstation.com", "PlayStation Plus üyeliğin yenilendi", ["playstation-plus"]),
    ("reply@email.playstation.com", "Satın alma makbuzu: oyun", []),
    ("xbox@xbox.com", "Xbox Game Pass Ultimate renewal", ["xbox-game-pass"]),
    ("account@microsoft.com", "Microsoft 365 Personal renewal", ["microsoft-365"]),
    ("account@microsoft.com", "Copilot Pro receipt", ["microsoft-copilot"]),
    ("no-reply@spotify.com", "Receipt", ["spotify"]),
    ("hello@max.com", "Your receipt", ["max"]),
    ("support@perplexity.ai", "Perplexity Pro receipt", ["perplexity-pro"]),
])
def test_sender_matching(sender, subject, expected):
    assert provider_catalog.match_sender(sender, subject) == expected


def test_lookalike_domains_do_not_match():
    assert provider_catalog.match_sender("billing@netflix.com.evil.example", "Receipt") == []
    assert provider_catalog.match_sender("billing@notnetflix.com", "Receipt") == []
    assert classify_email(EmailMessageMeta(sender="billing@netflix-support.co", subject="Your invoice", received_at="2026-01-01")) is None
