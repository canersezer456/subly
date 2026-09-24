"""Mailbox connections (Gmail / Outlook) for e-mail subscription discovery.

Flow (OAuth 2.0 authorization code + PKCE, confidential client):
  1. start()    — owner asks to connect; a one-time `state` + PKCE verifier are kept
                  server-side (collection `email_oauth_states`, 10-minute expiry) and the
                  browser is sent to the provider's consent screen.
  2. complete() — provider redirects back to the backend callback; state must exist,
                  be unexpired, belong to the *currently signed-in* user and is consumed.
                  The code is exchanged server-side; only the refresh token is kept,
                  encrypted (token_crypto). Access tokens are never stored.
  3. sync()     — refreshes an access token, reads *header metadata only* (From,
                  Subject, Date) of recent messages, classifies them in memory and
                  writes pending discovery candidates. Message data is not persisted.
  4. disconnect() — revokes (Google) and deletes the stored token.

Scopes are the narrowest read-only ones that still allow sender/subject/date:
  Gmail   https://www.googleapis.com/auth/gmail.metadata  (no message bodies)
  Outlook Mail.ReadBasic + offline_access                  (no bodies/attachments)
Signing in with Google does NOT grant any of this; it is a separate, explicit consent.

Nothing here logs tokens, codes, message headers or provider responses.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from lib import log_redaction
from lib.db import db
from lib.discovery import candidates as candidate_service
from lib.discovery import token_crypto
from lib.discovery.email_source import EmailMessageMeta, classify_email

log_redaction.install()  # the OAuth callback URL carries code/state; keep them out of access logs

STATES = "email_oauth_states"
CONNECTIONS = "email_connections"
STATE_TTL = timedelta(minutes=10)
LOOKBACK_DAYS = 400


@dataclass(frozen=True)
class MailProvider:
    id: str
    name: str
    client_id_env: str
    client_secret_env: str
    redirect_uri_env: str
    scopes: tuple[str, ...]
    required_scope: str  # must appear in the granted scopes, else the connection is refused
    revoke_url: str | None = None
    extra_auth_params: dict = field(default_factory=dict)

    @property
    def tenant(self) -> str:
        return os.environ.get("OUTLOOK_OAUTH_TENANT", "common").strip() or "common"

    @property
    def authorize_url(self) -> str:
        if self.id == "gmail":
            return "https://accounts.google.com/o/oauth2/v2/auth"
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        if self.id == "gmail":
            return "https://oauth2.googleapis.com/token"
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"

    def env(self) -> dict[str, str]:
        return {
            "client_id": os.environ.get(self.client_id_env, "").strip(),
            "client_secret": os.environ.get(self.client_secret_env, "").strip(),
            "redirect_uri": os.environ.get(self.redirect_uri_env, "").strip(),
        }

    def missing_config(self) -> list[str]:
        """Names (never values) of the environment variables still missing."""
        values = self.env()
        missing = [name for name, key in ((self.client_id_env, "client_id"), (self.client_secret_env, "client_secret"), (self.redirect_uri_env, "redirect_uri")) if not values[key]]
        if not token_crypto.is_configured():
            missing.append(token_crypto.KEY_ENV)
        return missing

    def is_configured(self) -> bool:
        return not self.missing_config()


GMAIL = MailProvider(
    id="gmail",
    name="Gmail",
    client_id_env="GMAIL_OAUTH_CLIENT_ID",
    client_secret_env="GMAIL_OAUTH_CLIENT_SECRET",
    redirect_uri_env="GMAIL_OAUTH_REDIRECT_URI",
    scopes=("https://www.googleapis.com/auth/gmail.metadata",),
    required_scope="https://www.googleapis.com/auth/gmail.metadata",
    revoke_url="https://oauth2.googleapis.com/revoke",
    # offline + consent => a refresh token is issued; do not merge previously granted scopes.
    extra_auth_params={"access_type": "offline", "prompt": "consent", "include_granted_scopes": "false"},
)
OUTLOOK = MailProvider(
    id="outlook",
    name="Outlook",
    client_id_env="OUTLOOK_OAUTH_CLIENT_ID",
    client_secret_env="OUTLOOK_OAUTH_CLIENT_SECRET",
    redirect_uri_env="OUTLOOK_OAUTH_REDIRECT_URI",
    scopes=("offline_access", "https://graph.microsoft.com/Mail.ReadBasic"),
    required_scope="Mail.ReadBasic",
    extra_auth_params={"prompt": "select_account"},
)
PROVIDERS: dict[str, MailProvider] = {GMAIL.id: GMAIL, OUTLOOK.id: OUTLOOK}


class MailboxError(RuntimeError):
    """Expected failure with a short machine code (safe to show / put in a redirect)."""

    def __init__(self, code: str, message: str = "", *, retryable: bool = False):
        super().__init__(message or code)
        self.code = code
        self.retryable = retryable


# Only these exact structured reasons may cross the provider-response boundary.
# Messages, ErrorInfo metadata/domain, URLs and unknown reasons are never logged.
_GOOGLE_REASONS = {
    "accessNotConfigured": "provider_configuration",
    "SERVICE_DISABLED": "provider_configuration",
    "API_KEY_INVALID": "provider_configuration",
    "invalid_client": "provider_configuration",
    "unauthorized_client": "provider_configuration",
    "insufficientPermissions": "scope_missing",
    "ACCESS_TOKEN_SCOPE_INSUFFICIENT": "scope_missing",
    "invalid_scope": "scope_missing",
    "domainPolicy": "provider_policy",
    "ORG_RESTRICTION_VIOLATION": "provider_policy",
    "SECURITY_POLICY_VIOLATED": "provider_policy",
    "admin_policy_enforced": "provider_policy",
    "access_denied": "provider_policy",
    "rateLimitExceeded": "provider_quota",
    "userRateLimitExceeded": "provider_quota",
    "dailyLimitExceeded": "provider_quota",
    "quotaExceeded": "provider_quota",
    "RATE_LIMIT_EXCEEDED": "provider_quota",
    "QUOTA_EXCEEDED": "provider_quota",
    "authError": "reauth_required",
    "invalid_grant": "reauth_required",
    "invalid_token": "reauth_required",
    "ACCESS_TOKEN_EXPIRED": "reauth_required",
    "ACCESS_TOKEN_INVALID": "reauth_required",
}
_logger = logging.getLogger(__name__)


def _google_error(response: httpx.Response, operation: str) -> MailboxError:
    reasons = []
    try:
        body = response.json()
    except ValueError:
        body = None
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, str):
        reasons.append(error)
    elif isinstance(error, dict):
        entries = error.get("errors")
        if isinstance(entries, list):
            reasons.extend(item.get("reason") for item in entries if isinstance(item, dict))
        details = error.get("details")
        if isinstance(details, list):
            reasons.extend(item.get("reason") for item in details if isinstance(item, dict) and item.get("@type") == "type.googleapis.com/google.rpc.ErrorInfo")
    recognized = {r for r in reasons if isinstance(r, str) and r in _GOOGLE_REASONS}
    # Authentication/scope failures win over quota hints in mixed responses.
    priority = ("reauth_required", "scope_missing", "provider_configuration", "provider_policy", "provider_quota")
    reason = next((r for code in priority for r in sorted(recognized) if _GOOGLE_REASONS[r] == code), "unknown")
    status = response.status_code
    # A service failure must never invalidate a stored grant.
    if status >= 500:
        code = "provider_unavailable"
    elif status == 429:
        code = "provider_quota"
    elif reason != "unknown":
        code = _GOOGLE_REASONS[reason]
    elif status == 401 and operation != "refresh":
        code = "reauth_required"
    else:
        code = "provider_forbidden" if status == 403 else "provider_unavailable"
    safe_operation = operation if operation in ("exchange", "refresh", "list", "metadata") else "unknown"
    _logger.warning("mailbox provider=gmail operation=%s status=%d reason=%s", safe_operation, status, reason)
    retryable = status == 429 or 500 <= status <= 599 or (
        status == 403 and code == "provider_quota" and reason in {
            "rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED",
        }
    )
    return MailboxError(code, retryable=retryable)


def _retry_after_seconds(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    val = response.headers.get("Retry-After")
    if not val:
        return None
    try:
        secs = float(val)
        if 0 < secs <= 20:
            return secs
    except (ValueError, TypeError):
        pass
    return None


async def _retry_pause(attempt: int, retry_after: float | None = None) -> None:
    # Bounded exponential backoff (attempt 0: 1.0s, attempt 1: 2.0s) + jitter.
    # If the provider specifies a valid Retry-After <= 20s, honor at least that wait.
    base_delay = 1.0 * (2 ** attempt) + secrets.randbelow(350) / 1000
    delay = max(base_delay, retry_after or 0.0)
    await asyncio.sleep(min(delay, 20.0))


async def _google_request(client: httpx.AsyncClient, method: str, url: str, operation: str, **kwargs) -> httpx.Response:
    for attempt in range(3):
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.HTTPError:
            error = MailboxError("provider_unavailable", retryable=True)
            retry_after = None
        else:
            if response.status_code == 200 or (operation == "metadata" and response.status_code == 404):
                return response
            error = _google_error(response, operation)
            retry_after = _retry_after_seconds(response)
        if not error.retryable or attempt == 2:
            raise error from None
        await _retry_pause(attempt, retry_after)
    raise AssertionError("unreachable")


def _token_payload(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        raise MailboxError("provider_unavailable") from None
    if not isinstance(payload, dict):
        raise MailboxError("provider_unavailable")
    return payload


def http_client() -> httpx.AsyncClient:
    """Factory so tests can swap in an httpx.MockTransport. Never logs bodies."""
    return httpx.AsyncClient(timeout=20)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def get_provider(provider_id: str) -> MailProvider:
    provider = PROVIDERS.get(provider_id)
    if not provider:
        raise MailboxError("unknown_provider")
    return provider


# ---- 1. start ------------------------------------------------------------------


async def start(user_id: str, provider_id: str) -> str:
    provider = get_provider(provider_id)
    if not provider.is_configured():
        raise MailboxError("not_configured")
    cfg = provider.env()
    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()
    await db[STATES].delete_many({"user_id": user_id, "provider": provider.id})  # one pending flow per provider
    await db[STATES].insert_one({"state": state, "user_id": user_id, "provider": provider.id, "code_verifier": verifier, "created_at": _now(), "expires_at": _now() + STATE_TTL})
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(provider.scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        **provider.extra_auth_params,
    }
    return f"{provider.authorize_url}?{urlencode(params)}"


# ---- 2. complete ---------------------------------------------------------------


def _granted(provider: MailProvider, scope_string: str) -> bool:
    if not isinstance(scope_string, str):
        return False
    granted = {s.strip().lower() for s in scope_string.split()}
    wanted = provider.required_scope.lower()
    return any(g == wanted or g.endswith("/" + wanted) for g in granted)


async def complete(user_id: str, provider_id: str, code: str, state: str) -> None:
    provider = get_provider(provider_id)
    if not provider.is_configured():
        raise MailboxError("not_configured")
    pending = await db[STATES].find_one({"state": state, "provider": provider.id})
    if not pending:
        raise MailboxError("state_invalid")
    await db[STATES].delete_one({"state": state})  # single use, whatever happens next
    if pending["user_id"] != user_id:
        raise MailboxError("state_invalid")
    if _aware(pending["expires_at"]) < _now():
        raise MailboxError("state_expired")

    cfg = provider.env()
    try:
        async with http_client() as client:
            response = await client.post(provider.token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code_verifier": pending["code_verifier"],
            })
    except httpx.HTTPError as exc:
        raise MailboxError("exchange_failed") from exc
    if response.status_code != 200:
        if provider.id == "gmail":
            raise _google_error(response, "exchange")
        raise MailboxError("exchange_failed")
    payload = _token_payload(response)
    refresh_token = payload.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise MailboxError("no_refresh_token")
    if not _granted(provider, payload.get("scope", "")):
        raise MailboxError("scope_missing")

    now = _now().isoformat()
    existing = await db[CONNECTIONS].find_one({"user_id": user_id, "provider": provider.id}, {"_id": 0})
    doc = {
        "user_id": user_id,
        "provider": provider.id,
        "refresh_token_enc": token_crypto.encrypt(refresh_token),
        "scopes": sorted(set((payload.get("scope") or "").split())),
        "status": "connected",
        "connected_at": now,
        "updated_at": now,
    }
    if existing:
        await db[CONNECTIONS].update_one({"user_id": user_id, "provider": provider.id}, {"$set": doc})
    else:
        await db[CONNECTIONS].insert_one({"id": str(uuid.uuid4()), "last_sync_at": None, "last_sync": None, **doc})


# ---- 3. sync ---------------------------------------------------------------------


async def _connection(user_id: str, provider_id: str) -> dict:
    conn = await db[CONNECTIONS].find_one({"user_id": user_id, "provider": provider_id}, {"_id": 0})
    if not conn:
        raise MailboxError("not_connected")
    return conn


async def _access_token(provider: MailProvider, conn: dict, client: httpx.AsyncClient) -> str:
    cfg = provider.env()
    try:
        refresh_token = token_crypto.decrypt(conn["refresh_token_enc"])
    except token_crypto.TokenCryptoUnavailable as exc:
        raise MailboxError("token_unreadable") from exc
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": cfg["client_id"], "client_secret": cfg["client_secret"]}
    if provider.id == "outlook":
        data["scope"] = " ".join(provider.scopes)
    if provider.id == "gmail":
        response = await _google_request(client, "POST", provider.token_url, "refresh", data=data)
    else:
        response = await client.post(provider.token_url, data=data)
    if response.status_code != 200:
        if provider.id == "gmail":
            raise _google_error(response, "refresh")
        # Do not mistake an OAuth client/configuration failure for a revoked grant.
        error = _token_payload(response).get("error")
        if response.status_code in (400, 401) and error == "invalid_grant":
            raise MailboxError("reauth_required")
        raise MailboxError("provider_unavailable")
    payload = _token_payload(response)
    # OAuth permits scope to be omitted when unchanged; an explicit scope must suffice.
    if "scope" in payload and not _granted(provider, payload["scope"]):
        raise MailboxError("scope_missing")
    if not isinstance(payload.get("access_token"), str) or not payload["access_token"]:
        raise MailboxError("provider_unavailable")
    rotated = payload.get("refresh_token")
    if rotated is not None and (not isinstance(rotated, str) or not rotated):
        raise MailboxError("provider_unavailable")
    if rotated and rotated != refresh_token:  # Microsoft rotates refresh tokens
        await db[CONNECTIONS].update_one({"user_id": conn["user_id"], "provider": provider.id}, {"$set": {"refresh_token_enc": token_crypto.encrypt(rotated)}})
    return payload["access_token"]


def _header(headers: list[dict], name: str) -> str:
    return next((h.get("value", "") for h in headers if h.get("name", "").lower() == name.lower()), "")


@dataclass
class MailFetch:
    messages: list[EmailMessageMeta] = field(default_factory=list)
    skipped: int = 0


async def _gmail_messages(client: httpx.AsyncClient, token: str, since: date, limit: int) -> MailFetch:
    base = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    auth = {"Authorization": f"Bearer {token}"}
    sem = asyncio.Semaphore(2)
    since_ms = int(datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)

    async def meta(message_id: str) -> tuple[int, EmailMessageMeta] | MailboxError:
        try:
            async with sem:
                # Explicit projection excludes snippet, bodies, attachments and unrelated headers.
                r = await _google_request(client, "GET", f"{base}/{message_id}", "metadata", headers=auth, params=[("format", "metadata"), ("fields", "internalDate,payload/headers"), ("metadataHeaders", "From"), ("metadataHeaders", "Subject")])
        except MailboxError as exc:
            return exc
        if r.status_code == 404:  # deleted between list and get
            return MailboxError("provider_unavailable", retryable=True)
        body = _token_payload(r)
        try:
            raw_date = body["internalDate"]
            if not isinstance(raw_date, (str, int)) or isinstance(raw_date, bool):
                raise ValueError
            received = int(raw_date)
            if received < 0:
                raise ValueError
            headers = body["payload"]["headers"]
            if not isinstance(headers, list) or any(
                not isinstance(h, dict) or not isinstance(h.get("name"), str) or not isinstance(h.get("value"), str)
                for h in headers
            ):
                raise ValueError
            when = datetime.fromtimestamp(received / 1000, tz=timezone.utc).date().isoformat()
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            raise MailboxError("provider_unavailable") from None
        return received, EmailMessageMeta(sender=_header(headers, "From"), subject=_header(headers, "Subject"), received_at=when)

    result = MailFetch()
    page_token = None
    seen_pages: set[str] = set()
    seen_ids: set[str] = set()
    fetched = 0
    last_skipped = None
    # Bound both requests and unique IDs, even for duplicate or empty provider pages.
    for _ in range(limit):
        remaining = limit - len(seen_ids)
        if remaining <= 0:
            break
        params = {"maxResults": min(100, remaining), "fields": "messages/id,nextPageToken"}
        if page_token:
            params["pageToken"] = page_token
        r = await _google_request(client, "GET", base, "list", headers=auth, params=params)
        listing = _token_payload(r)
        entries = listing.get("messages", [])
        if not isinstance(entries, list):
            raise MailboxError("provider_unavailable")
        ids = []
        for entry in entries[:params["maxResults"]]:
            message_id = entry.get("id") if isinstance(entry, dict) else None
            # IDs become path segments: never follow a provider-supplied URL/path.
            if not isinstance(message_id, str) or not message_id or len(message_id) > 256 or not all(c.isascii() and (c.isalnum() or c in "-_") for c in message_id):
                raise MailboxError("provider_unavailable")
            if message_id not in seen_ids and len(ids) < remaining:
                seen_ids.add(message_id)
                ids.append(message_id)
        # Finish this bounded batch before raising; no orphan requests using a closed client.
        results = await asyncio.gather(*(meta(message_id) for message_id in ids), return_exceptions=True)
        for item in results:
            if isinstance(item, BaseException):
                if isinstance(item, MailboxError) and item.retryable:
                    result.skipped += 1
                    last_skipped = item
                    continue
                raise item
            received, message = item
            fetched += 1
            if received >= since_ms:
                result.messages.append(message)
        page_token = listing.get("nextPageToken")
        if page_token is None or page_token == "":
            break
        if not isinstance(page_token, str) or page_token in seen_pages:
            raise MailboxError("provider_unavailable")
        seen_pages.add(page_token)
    else:
        if page_token and len(seen_ids) < limit:
            raise MailboxError("provider_unavailable")
    if result.skipped and not fetched:
        raise last_skipped
    return result


async def _outlook_messages(client: httpx.AsyncClient, token: str, since: date, limit: int) -> list[EmailMessageMeta]:
    auth = {"Authorization": f"Bearer {token}"}
    url: str | None = "https://graph.microsoft.com/v1.0/me/messages"
    params: dict | None = {
        "$select": "from,subject,receivedDateTime",
        "$filter": f"receivedDateTime ge {since.isoformat()}T00:00:00Z",
        "$orderby": "receivedDateTime desc",
        "$top": "100",
    }
    out: list[EmailMessageMeta] = []
    while url and len(out) < limit:
        r = await client.get(url, headers=auth, params=params)
        if r.status_code == 401:
            raise MailboxError("reauth_required")
        if r.status_code == 403:
            raise MailboxError("provider_forbidden")
        if r.status_code != 200:
            raise MailboxError("provider_unavailable")
        body = r.json()
        for item in body.get("value", []):
            address = ((item.get("from") or {}).get("emailAddress") or {}).get("address", "")
            out.append(EmailMessageMeta(sender=address, subject=item.get("subject") or "", received_at=(item.get("receivedDateTime") or "")[:10]))
        url, params = body.get("@odata.nextLink"), None  # nextLink already carries the query
    return out[:limit]


def sync_limit() -> int:
    try:
        return max(1, min(int(os.environ.get("EMAIL_SYNC_MAX_MESSAGES", "500")), 5000))
    except ValueError:
        return 500


async def sync(user_id: str, provider_id: str, today: date) -> dict:
    provider = get_provider(provider_id)
    if not provider.is_configured():
        raise MailboxError("not_configured")
    conn = await _connection(user_id, provider.id)
    if conn.get("status") != "connected":
        raise MailboxError("reauth_required")
    since = today - timedelta(days=LOOKBACK_DAYS)
    try:
        async with http_client() as client:
            token = await _access_token(provider, conn, client)
            if provider.id == "gmail":
                fetched = await _gmail_messages(client, token, since, sync_limit())
            else:
                fetched = MailFetch(await _outlook_messages(client, token, since, sync_limit()))
            messages = fetched.messages
    except MailboxError as exc:
        if exc.code in ("reauth_required", "scope_missing"):
            await db[CONNECTIONS].update_one({"user_id": user_id, "provider": provider.id}, {"$set": {"status": "reauth_required", "updated_at": _now().isoformat()}})
        raise
    except httpx.HTTPError as exc:
        raise MailboxError("provider_unavailable") from exc

    # Classified in memory; only the resulting sender domain / signal / date reach the DB.
    classified = [c for c in (classify_email(m) for m in messages) if c]
    drafts = candidate_service.email_drafts(classified, source=provider.id)
    result = await candidate_service.upsert_candidates(user_id, drafts)
    summary = {"scanned": len(messages), "matched": len(classified), "created": result["created"], "merged": result["merged"], "skipped_rejected": result["skipped_rejected"], "already_accepted": result["already_accepted"], "partial": fetched.skipped > 0, "skipped": fetched.skipped}
    await db[CONNECTIONS].update_one({"user_id": user_id, "provider": provider.id}, {"$set": {"last_sync_at": _now().isoformat(), "last_sync": summary}})
    return {**summary, "candidate_ids": result["ids"]}


# ---- 4. disconnect ---------------------------------------------------------------


async def disconnect(user_id: str, provider_id: str) -> bool:
    provider = get_provider(provider_id)
    conn = await db[CONNECTIONS].find_one({"user_id": user_id, "provider": provider.id}, {"_id": 0})
    if not conn:
        return False
    if provider.revoke_url:
        try:
            token = token_crypto.decrypt(conn["refresh_token_enc"])
            async with http_client() as client:
                await client.post(provider.revoke_url, data={"token": token})
        except (httpx.HTTPError, token_crypto.TokenCryptoUnavailable):
            pass  # best effort; the stored token is deleted below regardless
    await db[CONNECTIONS].delete_one({"user_id": user_id, "provider": provider.id})
    await db[STATES].delete_many({"user_id": user_id, "provider": provider.id})
    return True


async def delete_all_for_user(user_id: str) -> None:
    for provider_id in PROVIDERS:
        await disconnect(user_id, provider_id)
    await db[STATES].delete_many({"user_id": user_id})


# ---- status ---------------------------------------------------------------------


async def status(user_id: str) -> dict:
    adapters = []
    for provider in PROVIDERS.values():
        conn = await db[CONNECTIONS].find_one({"user_id": user_id, "provider": provider.id}, {"_id": 0, "refresh_token_enc": 0})
        configured = provider.is_configured()
        if conn and conn.get("status") == "connected" and configured:
            state = "connected"
        elif conn:
            state = "reauth_required" if configured else "not_configured"
        else:
            state = "available" if configured else "not_configured"
        adapters.append({
            "id": provider.id,
            "name": provider.name,
            "configured": configured,
            "connected": state == "connected",
            "state": state,
            "scope": " ".join(provider.scopes),
            "connected_at": (conn or {}).get("connected_at"),
            "last_sync_at": (conn or {}).get("last_sync_at"),
            "last_sync": (conn or {}).get("last_sync"),
        })
    any_connected = any(a["connected"] for a in adapters)
    return {
        "available": any(a["configured"] for a in adapters),
        "connected": any_connected,
        "state": "connected" if any_connected else ("available" if any(a["configured"] for a in adapters) else "not_configured"),
        "adapters": adapters,
    }
