import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from lib import finance, provider_catalog, subscription_insights
from lib.auth import get_current_user
from lib.db import db
from lib.discovery import candidates as candidate_service
from lib.discovery import importer, mailbox, transactions
from models.subscription import (
    SOURCES,
    CandidateAcceptRequest,
    CandidateAcceptResponse,
    CandidateImportRequest,
    CandidateImportResponse,
    Deal,
    DiscoveryCandidate,
    DiscoveryStatus,
    DuplicateMatch,
    EmailConnectResponse,
    EmailSyncResponse,
    MockScanResponse,
    Provider,
    Subscription,
    SubscriptionCreate,
    SubscriptionCreateRequest,
    SubscriptionInsights,
    SubscriptionUpdateRequest,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Rows written by this version carry schema_version=2 and a trustworthy `source`.
# Rows without it predate source tracking: their stored `source` is unreliable
# (the old starter fixture labelled rows "manual"/"mock_scan"), so they are
# reported as "legacy" — never relabelled as email/transaction, never deleted.
SCHEMA_VERSION = 2
DEFAULT_CANCEL_URL = "https://www.google.com"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _subscription(doc: dict) -> Subscription:
    legacy = not doc.get("schema_version")
    source = "legacy" if legacy else (doc.get("source") if doc.get("source") in SOURCES else "manual")
    return Subscription(**{**doc, "source": source, "legacy": legacy, "legacy_reviewed": bool(doc.get("legacy_reviewed_at")), "note": doc.get("note") or ""})


async def _user_subscriptions(user_id: str) -> list[dict]:
    return await db.subscriptions.find({"user_id": user_id}, {"_id": 0}).to_list(None)


def _duplicate_matches(subs: list[dict], provider_id: str | None, name: str) -> list[dict]:
    ids = [provider_id] if provider_id else []
    guessed = provider_catalog.guess_provider_by_name(name)
    if guessed:
        ids.append(guessed["id"])
    return candidate_service.possible_duplicates(subs, ids, name)


def _duplicate_conflict(matches: list[dict]) -> HTTPException:
    names = ", ".join(m["name"] for m in matches)
    return HTTPException(status_code=409, detail={"code": "possible_duplicate", "message": f"Mevcut aboneliğinle eşleşiyor olabilir: {names}", "matches": matches})


# ---- Collection ------------------------------------------------------------


@router.get("", response_model=list[Subscription])
async def list_subscriptions(user: dict = Depends(get_current_user)):
    docs = await db.subscriptions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("renewal_date", 1).to_list(None)
    return [_subscription(doc) for doc in docs]


@router.post("", response_model=Subscription)
async def create_subscription(input: SubscriptionCreateRequest, user: dict = Depends(get_current_user)):
    subs = await _user_subscriptions(user["user_id"])
    if not input.confirm_duplicate:
        matches = _duplicate_matches(subs, input.provider_id, input.name)
        if matches:
            raise _duplicate_conflict(matches)
    doc = input.model_dump(exclude={"confirm_duplicate"})
    provider = provider_catalog.get_provider(input.provider_id)
    if provider and doc.get("cancellation_url") in ("", DEFAULT_CANCEL_URL):
        doc["cancellation_url"] = provider["manage_url"]
    doc.update({
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        # A user-entered row is always "manual"; email/transaction/import are only
        # ever assigned server-side when the owner accepts a discovery candidate.
        "source": "manual",
        "schema_version": SCHEMA_VERSION,
        "price_history": [],
        "created_at": _now(),
    })
    await db.subscriptions.insert_one(doc)
    return _subscription(doc)


# ---- Reference data & derived views (static paths before /{subscription_id}) --


@router.get("/providers", response_model=list[Provider])
async def list_providers(q: str = Query(default="", max_length=60), limit: int = Query(default=60, ge=1, le=100), user: dict = Depends(get_current_user)):
    """Catalog search. Suggestions only — never creates a subscription."""
    return provider_catalog.search_providers(q, limit)


@router.get("/duplicates", response_model=list[DuplicateMatch])
async def duplicate_check(name: str = Query(default="", max_length=80), provider_id: str | None = Query(default=None, max_length=60), user: dict = Depends(get_current_user)):
    subs = await _user_subscriptions(user["user_id"])
    return _duplicate_matches(subs, provider_id, name)


@router.get("/insights", response_model=SubscriptionInsights)
async def insights(user: dict = Depends(get_current_user)):
    subs = await _user_subscriptions(user["user_id"])
    return subscription_insights.compute(subs, finance.today())


@router.get("/discovery/status", response_model=DiscoveryStatus)
async def discovery_status(user: dict = Depends(get_current_user)):
    pending = await db[candidate_service.COLLECTION].count_documents({"user_id": user["user_id"], "status": "pending"})
    return {"email": await mailbox.status(user["user_id"]), "transaction": transactions.status(), "manual_import": {"available": True, "connected": True, "state": "ready"}, "pending_candidates": pending}


# ---- Mailbox connections (Gmail / Outlook) ---------------------------------------
# Real OAuth: works only when the deployment has an OAuth client configured (see
# lib/discovery/mailbox.py for the environment variable names). Without it the
# endpoints answer 501 and nothing is read.

MAILBOX_HTTP = {
    "unknown_provider": 404, "not_configured": 501, "not_connected": 404,
    "reauth_required": 409, "scope_missing": 409, "token_unreadable": 409,
    "provider_unavailable": 502, "provider_configuration": 503,
    "provider_policy": 403, "provider_quota": 429, "provider_forbidden": 403,
}
MAILBOX_MESSAGES = {
    "unknown_provider": "Bilinmeyen e-posta sağlayıcısı",
    "not_configured": "E-posta bağlantısı bu sunucuda yapılandırılmadı (OAuth istemcisi yok). Hiçbir posta kutusu okunmadı.",
    "not_connected": "Bu e-posta hesabı bağlı değil",
    "reauth_required": "E-posta izni geçersiz; hesabı yeniden bağla",
    "token_unreadable": "Kayıtlı izin okunamadı; hesabı yeniden bağla",
    "provider_unavailable": "E-posta sağlayıcısına şu an ulaşılamıyor",
    "scope_missing": "E-posta üstbilgilerini okuma izni eksik; hesabı yeniden bağla ve gerekli izni ver",
    "provider_configuration": "E-posta hizmeti sunucuda doğru yapılandırılmamış veya API etkin değil. Sunucu yöneticisine başvur; hesabı yeniden bağlamak gerekmez.",
    "provider_policy": "E-posta erişimi sağlayıcı veya kuruluş politikası tarafından engellendi. Hesap yöneticisine başvur.",
    "provider_quota": "E-posta sağlayıcısının kullanım sınırına ulaşıldı. Daha sonra tekrar dene; hesabı yeniden bağlamak gerekmez.",
    "provider_forbidden": "E-posta sağlayıcısı erişimi reddetti. Erişim ayarlarını kontrol et veya yöneticine başvur.",
}


def _mailbox_http_error(exc: mailbox.MailboxError) -> HTTPException:
    return HTTPException(status_code=MAILBOX_HTTP.get(exc.code, 400), detail={"code": exc.code, "message": MAILBOX_MESSAGES.get(exc.code, "E-posta işlemi tamamlanamadı")})


def _app_redirect(**params: str) -> RedirectResponse:
    base = os.environ.get("APP_PUBLIC_URL", "").rstrip("/")
    return RedirectResponse(f"{base}/subscriptions?{urlencode({'tab': 'discover', **params})}", status_code=303)


@router.post("/discovery/email/{provider_id}/connect", response_model=EmailConnectResponse)
async def connect_email(provider_id: str, user: dict = Depends(get_current_user)):
    try:
        return {"authorization_url": await mailbox.start(user["user_id"], provider_id)}
    except mailbox.MailboxError as exc:
        raise _mailbox_http_error(exc) from exc


@router.get("/discovery/email/{provider_id}/callback", include_in_schema=False)
async def email_oauth_callback(provider_id: str, request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    """Browser lands here from the provider's consent screen. Always redirects back to
    the app with a short status code — never echoes tokens or provider errors."""
    try:
        user = await get_current_user(request)
    except HTTPException:
        return _app_redirect(email="error", provider=provider_id, reason="session")
    if error or not code or not state:
        if state:  # consume the pending state so it cannot be replayed
            await db[mailbox.STATES].delete_many({"state": state, "user_id": user["user_id"]})
        return _app_redirect(email="error", provider=provider_id, reason="denied")
    try:
        await mailbox.complete(user["user_id"], provider_id, code, state)
    except mailbox.MailboxError as exc:
        return _app_redirect(email="error", provider=provider_id, reason=exc.code)
    return _app_redirect(email="connected", provider=provider_id)


@router.post("/discovery/email/{provider_id}/sync", response_model=EmailSyncResponse)
async def sync_email(provider_id: str, user: dict = Depends(get_current_user)):
    """Reads header metadata of recent mail and creates *pending candidates* only."""
    try:
        result = await mailbox.sync(user["user_id"], provider_id, finance.today())
    except mailbox.MailboxError as exc:
        raise _mailbox_http_error(exc) from exc
    subs = await _user_subscriptions(user["user_id"])
    rows = []
    for cid in result.pop("candidate_ids"):
        doc = await candidate_service.get_candidate(user["user_id"], cid)
        if doc:
            rows.append(candidate_service.public_candidate(doc, subs))
    return {**result, "candidates": rows}


@router.delete("/discovery/email/{provider_id}", status_code=204)
async def disconnect_email(provider_id: str, user: dict = Depends(get_current_user)):
    try:
        removed = await mailbox.disconnect(user["user_id"], provider_id)
    except mailbox.MailboxError as exc:
        raise _mailbox_http_error(exc) from exc
    if not removed:
        raise HTTPException(status_code=404, detail={"code": "not_connected", "message": MAILBOX_MESSAGES["not_connected"]})


@router.post("/mock-scan", response_model=MockScanResponse)
async def mock_scan(user: dict = Depends(get_current_user)):
    from lib.seed import DEMO_EMAIL
    if user.get("email") != DEMO_EMAIL:
        raise HTTPException(status_code=409, detail="Abonelik keşfi bağlı bir posta hesabı gerektirir; bu entegrasyon henüz mevcut değil.")
    return MockScanResponse(scan_id=f"scan_{uuid.uuid4().hex[:10]}", detected=[
        SubscriptionCreate(name="Amazon Prime", category="Eğlence", price=39.90, currency="TRY", renewal_date="2026-04-08", payment_method="Kart •••• 4821", cancellation_url="https://www.amazon.com/gp/subs/primeclub", source="mock_scan"),
        SubscriptionCreate(name="ChatGPT Plus", category="İş / Yazılım", price=20, currency="USD", renewal_date="2026-04-12", payment_method="Kart •••• 1190", cancellation_url="https://chatgpt.com/settings", source="mock_scan"),
    ])


@router.get("/deals", response_model=list[Deal])
async def deals(user: dict = Depends(get_current_user)):
    return [
        Deal(id="deal_1", title="Yıllık plana geç", provider="Spotify", category="Müzik", description="Yıllık ödeme seçeneğiyle aylık ortalama maliyetini düşür.", current_price=59.99, discounted_price=49.99, savings=120, url="https://www.spotify.com/account/subscription/", badge="2 ay avantaj", discount_percent=17, featured=True),
        Deal(id="deal_2", title="Aile paketini keşfet", provider="YouTube Premium", category="Eğlence", description="Aynı hanedeki kullanıcılarla aile planının kişi başı maliyetini keşfet.", current_price=79.99, discounted_price=49.99, savings=360, url="https://www.youtube.com/paid_memberships", badge="Aile planı", discount_percent=38),
        Deal(id="deal_3", title="Öğrenci planı", provider="Adobe Creative Cloud", category="İş / Yazılım", description="Uygun öğrenciler için sağlayıcının doğrulama gerektiren eğitim planını incele.", current_price=699, discounted_price=349, savings=4200, url="https://www.adobe.com/creativecloud/plans.html", badge="Öğrenci", discount_percent=50, featured=True),
        Deal(id="deal_4", title="Prime avantajlarını keşfet", provider="Amazon Prime", category="Eğlence", description="Video, teslimat ve oyun avantajlarını tek üyelikte karşılaştır.", current_price=49.90, discounted_price=39.90, savings=120, url="https://www.amazon.com.tr/amazonprime", badge="Paket avantajı", discount_percent=20),
        Deal(id="deal_5", title="Yıllık depolama planı", provider="Google One", category="Bulut", description="Aylık ve yıllık depolama seçeneklerini ihtiyacına göre karşılaştır.", current_price=49.99, discounted_price=41.99, savings=96, url="https://one.google.com/about/plans", badge="Yıllık plan", discount_percent=16),
        Deal(id="deal_6", title="Ekip planına geçiş", provider="ChatGPT Plus", category="İş / Yazılım", description="Bireysel ve ekip planlarını kullanım yoğunluğuna göre karşılaştır.", current_price=20, discounted_price=18, savings=24, currency="USD", url="https://chatgpt.com/pricing", badge="Ekip planı", discount_percent=10),
    ]


# ---- Discovery candidates ------------------------------------------------------


@router.get("/candidates", response_model=list[DiscoveryCandidate])
async def list_candidates(status: str | None = Query(default=None, pattern="^(pending|accepted|rejected)$"), user: dict = Depends(get_current_user)):
    return await candidate_service.list_candidates(user["user_id"], status)


@router.post("/candidates/import", response_model=CandidateImportResponse)
async def import_candidates(input: CandidateImportRequest, user: dict = Depends(get_current_user)):
    """User-supplied statement lines -> pending candidates. Writes nothing to subscriptions.
    The pasted text is parsed in memory only; it is neither stored nor logged."""
    try:
        txns, skipped = importer.parse_statement(input.text)
    except importer.ImportTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    drafts = transactions.detect_recurring(txns, evidence_type="manual_import", evidence_source="import", today=finance.today())
    result = await candidate_service.upsert_candidates(user["user_id"], drafts)
    subs = await _user_subscriptions(user["user_id"])
    rows = []
    for cid in result["ids"]:
        doc = await candidate_service.get_candidate(user["user_id"], cid)
        if doc:
            rows.append(candidate_service.public_candidate(doc, subs))
    return {"parsed_transactions": len(txns), "skipped_lines": skipped, "created": result["created"], "merged": result["merged"], "skipped_rejected": result["skipped_rejected"], "already_accepted": result["already_accepted"], "candidates": rows}


async def _owned_candidate(user_id: str, candidate_id: str) -> dict:
    doc = await candidate_service.get_candidate(user_id, candidate_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Aday bulunamadı")
    return doc


@router.post("/candidates/{candidate_id}/accept", response_model=CandidateAcceptResponse)
async def accept_candidate(candidate_id: str, input: CandidateAcceptRequest, user: dict = Depends(get_current_user)):
    candidate = await _owned_candidate(user["user_id"], candidate_id)
    if candidate["status"] != "pending":
        raise HTTPException(status_code=409, detail="Bu aday zaten işlendi")

    allowed = [pid for pid in [candidate.get("provider_id"), *candidate.get("alternatives", [])] if pid]
    provider_id = input.provider_id or candidate.get("provider_id")
    if provider_id and provider_id not in allowed:
        raise HTTPException(status_code=422, detail="Seçilen servis bu adayla ilişkili değil")
    provider = provider_catalog.get_provider(provider_id)
    if candidate.get("ambiguous") and not provider and not input.name:
        raise HTTPException(status_code=422, detail="Belirsiz aday: hangi servis olduğunu seç")

    price = input.price if input.price is not None else candidate.get("suggested_price")
    renewal = input.renewal_date or candidate.get("renewal_date")
    if not price or not renewal:
        raise HTTPException(status_code=422, detail="Fiyat ve yenileme tarihi gerekli")
    currency = input.currency or candidate.get("currency") or "TRY"
    if currency not in ("TRY", "USD", "EUR"):
        raise HTTPException(status_code=422, detail="Geçersiz para birimi")
    name = input.name or (provider["name"] if provider else candidate["provider_name"])

    subs = await _user_subscriptions(user["user_id"])
    if not input.confirm_duplicate:
        matches = _duplicate_matches(subs, provider_id, name)
        if matches:
            raise _duplicate_conflict(matches)

    evidence_types = sorted({e["type"] for e in candidate.get("evidence", [])})
    source = next((candidate_service.SOURCE_FOR_EVIDENCE[t] for t in ("transaction", "email", "manual_import", "other") if t in evidence_types), "import")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "name": name,
        "category": provider_catalog.CATEGORY_TO_SUBSCRIPTION.get(provider["category"], "Diğer") if provider else "Diğer",
        "price": float(price),
        "currency": currency,
        "renewal_date": renewal,
        "payment_method": input.payment_method,
        "cancellation_url": provider["manage_url"] if provider else DEFAULT_CANCEL_URL,
        "source": source,
        "billing_cycle": input.billing_cycle or candidate.get("billing_cycle") or "monthly",
        "usage": "active",
        "status": "active",
        "provider_id": provider_id if provider else None,
        "plan": input.plan or candidate.get("suggested_plan"),
        "note": input.note,
        "candidate_id": candidate["id"],
        "evidence_types": evidence_types,
        "schema_version": SCHEMA_VERSION,
        "price_history": [],
        "created_at": _now(),
    }
    subscription = _subscription(doc)  # validate before writing anything
    await db.subscriptions.insert_one(doc)
    await candidate_service.set_status(user["user_id"], candidate_id, "accepted", accepted_subscription_id=doc["id"])
    updated = await candidate_service.get_candidate(user["user_id"], candidate_id)
    return {"candidate": candidate_service.public_candidate(updated), "subscription": subscription}


@router.post("/candidates/{candidate_id}/reject", response_model=DiscoveryCandidate)
async def reject_candidate(candidate_id: str, user: dict = Depends(get_current_user)):
    candidate = await _owned_candidate(user["user_id"], candidate_id)
    if candidate["status"] != "pending":
        raise HTTPException(status_code=409, detail="Bu aday zaten işlendi")
    await candidate_service.set_status(user["user_id"], candidate_id, "rejected")
    return candidate_service.public_candidate(await candidate_service.get_candidate(user["user_id"], candidate_id))


# ---- Single subscription --------------------------------------------------------


async def _owned_subscription(user_id: str, subscription_id: str) -> dict:
    doc = await db.subscriptions.find_one({"id": subscription_id, "user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı")
    return doc


@router.get("/{subscription_id}", response_model=Subscription)
async def get_subscription(subscription_id: str, user: dict = Depends(get_current_user)):
    return _subscription(await _owned_subscription(user["user_id"], subscription_id))


@router.patch("/{subscription_id}", response_model=Subscription)
async def update_subscription(subscription_id: str, input: SubscriptionUpdateRequest, user: dict = Depends(get_current_user)):
    changes = input.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
    current = await _owned_subscription(user["user_id"], subscription_id)
    price_changed = "price" in changes and changes["price"] != current.get("price")
    currency_changed = "currency" in changes and changes["currency"] != current.get("currency", "TRY")
    if price_changed or currency_changed:
        history = list(current.get("price_history") or [])
        history.append({"price": current["price"], "currency": current.get("currency", "TRY"), "changed_at": _now()})
        changes["price_history"] = history[-24:]
    result = await db.subscriptions.update_one({"id": subscription_id, "user_id": user["user_id"]}, {"$set": changes})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı")
    doc = await db.subscriptions.find_one({"id": subscription_id, "user_id": user["user_id"]}, {"_id": 0})
    return _subscription(doc)


@router.post("/{subscription_id}/review", response_model=Subscription)
async def review_legacy(subscription_id: str, user: dict = Depends(get_current_user)):
    """Owner confirms a legacy row is really theirs. Only stamps a review time —
    the row's data and its "legacy" source label stay as they are."""
    await _owned_subscription(user["user_id"], subscription_id)
    await db.subscriptions.update_one({"id": subscription_id, "user_id": user["user_id"]}, {"$set": {"legacy_reviewed_at": _now()}})
    return _subscription(await _owned_subscription(user["user_id"], subscription_id))


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(subscription_id: str, user: dict = Depends(get_current_user)):
    result = await db.subscriptions.delete_one({"id": subscription_id, "user_id": user["user_id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı")
