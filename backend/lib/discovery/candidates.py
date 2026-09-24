"""Discovery candidates: "possibly a subscription", kept apart from real subscriptions.

Lifecycle: pending -> accepted (a subscription is created *by the owner's explicit
request*) or rejected. Every read/write here is scoped by user_id; callers pass the
authenticated user's id, never one taken from the request body.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from lib import provider_catalog
from lib.db import db

COLLECTION = "subscription_candidates"
STATUSES = ("pending", "accepted", "rejected")
EVIDENCE_TYPES = ("email", "transaction", "manual_import", "other")
# evidence type -> subscription.source once accepted
SOURCE_FOR_EVIDENCE = {"transaction": "transaction", "email": "email", "manual_import": "import", "other": "import"}
EVIDENCE_TEXT_TR = {
    "email": "E-posta faturasında tespit edildi",
    "transaction": "Düzenli ödeme hareketinde tespit edildi",
    "manual_import": "İçe aktardığın hesap dökümünde tespit edildi",
    "other": "Diğer kaynakta tespit edildi",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def confidence_label(confidence: float) -> str:
    """Numeric confidence stays internal; the UI only gets a descriptive bucket."""
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.5:
        return "medium"
    return "review"


def evidence_explanation(evidence: list[dict]) -> str:
    types = []
    for item in evidence:
        if item["type"] not in types:
            types.append(item["type"])
    if "email" in types and ("transaction" in types or "manual_import" in types):
        return "E-posta + ödeme hareketi eşleşti"
    return EVIDENCE_TEXT_TR.get(types[0], EVIDENCE_TEXT_TR["other"]) if types else EVIDENCE_TEXT_TR["other"]


def dedupe_key(draft: dict) -> str:
    if draft.get("provider_id"):
        return f"provider:{draft['provider_id']}"
    return f"ambiguous:{provider_catalog.fold(draft.get('provider_name', ''))}"


def possible_duplicates(subscriptions: list[dict], provider_ids: list[str], name: str | None = None) -> list[dict]:
    """Existing, not-cancelled subscriptions that *might* be the same service.

    Matching by provider id (incl. a candidate's alternatives), or — for rows without a
    provider id, like legacy data — by an exact catalog-name match of the row's name.
    Informational only: nothing is merged automatically.
    """
    wanted = {provider_catalog.PROVIDERS_BY_ID[pid]["family"] for pid in provider_ids if pid in provider_catalog.PROVIDERS_BY_ID}
    folded_name = provider_catalog.fold(name or "")
    matches = []
    for sub in subscriptions:
        if sub.get("status", "active") == "cancelled":
            continue
        sub_provider = provider_catalog.get_provider(sub.get("provider_id")) or provider_catalog.guess_provider_by_name(sub.get("name", ""))
        # Same product family (ChatGPT Plus vs Pro) counts: likely the same account, maybe a plan change.
        same_provider = bool(sub_provider and sub_provider["family"] in wanted)
        same_name = bool(folded_name and provider_catalog.fold(sub.get("name", "")) == folded_name)
        if same_provider or same_name:
            matches.append({"id": sub["id"], "name": sub["name"], "price": sub.get("price"), "currency": sub.get("currency", "TRY"), "status": sub.get("status", "active")})
    return matches


def public_candidate(doc: dict, subscriptions: list[dict] | None = None) -> dict:
    out = {k: v for k, v in doc.items() if k not in ("_id", "user_id", "dedupe_key")}
    out["confidence_label"] = confidence_label(doc.get("confidence", 0))
    out["explanation"] = evidence_explanation(doc.get("evidence", []))
    out["evidence_types"] = sorted({e["type"] for e in doc.get("evidence", [])})
    if subscriptions is not None and doc.get("status") == "pending":
        ids = [doc.get("provider_id")] + list(doc.get("alternatives", []))
        out["possible_duplicates"] = possible_duplicates(subscriptions, [i for i in ids if i], doc.get("provider_name"))
    else:
        out["possible_duplicates"] = []
    return out


async def list_candidates(user_id: str, status: str | None = None) -> list[dict]:
    query: dict = {"user_id": user_id}
    if status:
        query["status"] = status
    docs = await db[COLLECTION].find(query, {"_id": 0}).sort("created_at", -1).to_list(None)
    subs = await db.subscriptions.find({"user_id": user_id}, {"_id": 0}).to_list(None)
    return [public_candidate(doc, subs) for doc in docs]


async def get_candidate(user_id: str, candidate_id: str) -> dict | None:
    return await db[COLLECTION].find_one({"id": candidate_id, "user_id": user_id}, {"_id": 0})


def _merge_evidence(existing: list[dict], incoming: list[dict]) -> list[dict]:
    seen = {(e["type"], e.get("merchant") or e.get("sender_domain"), e.get("observed_at")) for e in existing}
    merged = list(existing)
    for item in incoming:
        key = (item["type"], item.get("merchant") or item.get("sender_domain"), item.get("observed_at"))
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged[-20:]


def _combined_confidence(old: float, new: float, evidence: list[dict]) -> float:
    types = {e["type"] for e in evidence}
    value = max(old, new)
    if "email" in types and ({"transaction", "manual_import"} & types):
        value = min(0.95, value + 0.15)  # two independent sources agree
    return round(value, 2)


async def upsert_candidates(user_id: str, drafts: list[dict]) -> dict:
    """Store drafts as pending candidates for `user_id`, deduplicating safely.

    - same provider already pending  -> merge evidence (no second row)
    - same provider previously rejected -> left rejected, not resurfaced
    - same provider already accepted -> not recreated
    Never touches `subscriptions`.
    """
    result = {"created": 0, "merged": 0, "skipped_rejected": 0, "already_accepted": 0, "ids": []}
    coll = db[COLLECTION]
    for draft in drafts:
        key = dedupe_key(draft)
        existing = await coll.find_one({"user_id": user_id, "dedupe_key": key}, {"_id": 0})
        if existing and existing["status"] == "rejected":
            result["skipped_rejected"] += 1
            continue
        if existing and existing["status"] == "accepted":
            result["already_accepted"] += 1
            continue
        if existing:
            evidence = _merge_evidence(existing.get("evidence", []), draft["evidence"])
            newer = max(e.get("observed_at", "") for e in draft["evidence"]) >= max((e.get("observed_at", "") for e in existing.get("evidence", [])), default="")
            changes = {
                "evidence": evidence,
                "confidence": _combined_confidence(existing.get("confidence", 0), draft["confidence"], evidence),
                "evidence_type": "multiple" if len({e["type"] for e in evidence}) > 1 else evidence[0]["type"],
                "updated_at": _now(),
            }
            if newer:
                for field in ("suggested_price", "currency", "billing_cycle", "renewal_date"):
                    if draft.get(field) is not None:
                        changes[field] = draft[field]
            await coll.update_one({"id": existing["id"], "user_id": user_id}, {"$set": changes})
            result["merged"] += 1
            result["ids"].append(existing["id"])
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "dedupe_key": key,
            "provider_id": draft.get("provider_id"),
            "provider_name": draft["provider_name"],
            "alternatives": draft.get("alternatives", []),
            "ambiguous": bool(draft.get("ambiguous")),
            "suggested_plan": draft.get("suggested_plan"),
            "suggested_price": draft.get("suggested_price"),
            "currency": draft.get("currency") or "TRY",
            "billing_cycle": draft.get("billing_cycle"),
            "renewal_date": draft.get("renewal_date"),
            "evidence_type": draft["evidence"][0]["type"],
            "evidence_source": draft["evidence"][0]["source"],
            "evidence": draft["evidence"],
            "confidence": draft["confidence"],
            "status": "pending",
            "created_at": _now(),
            "updated_at": _now(),
        }
        await coll.insert_one(doc)
        result["created"] += 1
        result["ids"].append(doc["id"])
    return result


async def set_status(user_id: str, candidate_id: str, status: str, **extra) -> bool:
    res = await db[COLLECTION].update_one({"id": candidate_id, "user_id": user_id}, {"$set": {"status": status, "updated_at": _now(), **extra}})
    return bool(res.matched_count)


def email_drafts(classifications: list[dict], source: str = "email") -> list[dict]:
    """Turn classify_email() results into candidate drafts (used once a mailbox adapter
    is connected). Ended subscriptions ("cancelled") are not proposed."""
    from lib.discovery.email_source import ACTIVE_SIGNALS

    by_provider: dict[tuple, list[dict]] = {}
    for item in classifications:
        if item["signal"] not in ACTIVE_SIGNALS:
            continue
        by_provider.setdefault(tuple(item["provider_ids"]), []).append(item)
    drafts = []
    for provider_ids, items in by_provider.items():
        providers = [p for p in (provider_catalog.get_provider(pid) for pid in provider_ids) if p]
        if not providers:
            continue
        # A sender like apple.com / google.com / microsoft.com maps to several services.
        ambiguous = not provider_catalog.same_family([p["id"] for p in providers])
        primary = None if ambiguous else providers[0]
        items.sort(key=lambda i: i["observed_at"])
        billing = {"renewal", "payment_confirmation", "invoice", "receipt"}
        confidence = 0.55 + (0.15 if any(i["signal"] in billing for i in items) else 0) + (0.1 if len(items) >= 2 else 0)
        if len(providers) > 1:
            confidence -= 0.1
        if primary is None:
            confidence = min(confidence, 0.35)  # which service is it? always "needs review"
        drafts.append({
            "provider_id": primary["id"] if primary else None,
            "provider_name": primary["name"] if primary else " / ".join(p["name"] for p in providers),
            "alternatives": [p["id"] for p in providers if not primary or p["id"] != primary["id"]],
            "ambiguous": primary is None,
            "suggested_plan": None,
            "suggested_price": None,  # prices are not taken from e-mail text
            "currency": primary.get("default_currency") if primary else None,
            "billing_cycle": None,
            "renewal_date": None,
            "confidence": round(min(confidence, 0.9), 2),
            "evidence": [{"type": "email", "source": source, "sender_domain": i["sender_domain"], "signal": i["signal"], "summary": f"{i['sender_domain']} · {i['signal']}", "observed_at": i["observed_at"]} for i in items[-5:]],
        })
    return drafts
