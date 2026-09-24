"""Subscription health/insights computed only from the caller's own rows.

Pure function over already user-scoped data. Amounts in other currencies are
converted with the same approximate rates the dashboard uses (lib.finance.RATES),
and the response says so via `rates`.
"""

from __future__ import annotations

from datetime import date, timedelta

from lib import finance, provider_catalog

# Only categories where "several of these" is a meaningful, neutral observation.
OVERLAP_CATEGORIES = ("streaming", "music", "ai", "cloud")


def _provider_of(sub: dict) -> dict | None:
    return provider_catalog.get_provider(sub.get("provider_id")) or provider_catalog.guess_provider_by_name(sub.get("name", ""))


def _bucket(rows: dict[str, list[dict]]) -> list[dict]:
    out = [{"key": key, "count": len(subs), "monthly_try": round(sum(finance.sub_monthly(s) for s in subs), 2)} for key, subs in rows.items()]
    return sorted(out, key=lambda b: (-b["monthly_try"], b["key"]))


def compute(subscriptions: list[dict], ref: date, horizon_days: int = 30) -> dict:
    active = finance.active_subs(subscriptions)
    monthly_total = round(sum(finance.sub_monthly(s) for s in active), 2)

    upcoming = []
    limit = ref + timedelta(days=horizon_days)
    for sub in active:
        nxt = finance.sub_next_renewal(sub, ref)
        if nxt <= limit:
            upcoming.append({"id": sub["id"], "name": sub["name"], "date": nxt.isoformat(), "days_until": (nxt - ref).days, "amount": sub["price"], "currency": sub.get("currency", "TRY"), "billing_cycle": finance.sub_cycle(sub)})
    upcoming.sort(key=lambda u: (u["date"], u["name"]))

    by_category: dict[str, list[dict]] = {}
    by_method: dict[str, list[dict]] = {}
    for sub in active:
        by_category.setdefault(sub.get("category") or "Diğer", []).append(sub)
        by_method.setdefault(sub.get("payment_method") or "", []).append(sub)

    yearly = [{"id": s["id"], "name": s["name"], "price": s["price"], "currency": s.get("currency", "TRY"), "monthly_equivalent_try": finance.sub_monthly(s)} for s in active if finance.sub_cycle(s) != "monthly"]

    price_changes = []
    for sub in subscriptions:
        history = sub.get("price_history") or []
        if not history:
            continue
        previous = history[-1]
        if previous.get("price") and previous["price"] != sub["price"]:
            price_changes.append({
                "id": sub["id"], "name": sub["name"], "previous_price": previous["price"], "current_price": sub["price"],
                "currency": sub.get("currency", "TRY"), "changed_at": previous["changed_at"],
                "change_percent": round((sub["price"] / previous["price"] - 1) * 100, 1),
            })

    groups: dict[str, list[dict]] = {}
    for sub in active:
        provider = _provider_of(sub)
        if provider and provider["category"] in OVERLAP_CATEGORIES:
            groups.setdefault(provider["category"], []).append(sub)
    overlaps = []
    for category, subs in groups.items():
        if len(subs) < 2:
            continue
        label = provider_catalog.CATEGORY_LABELS_TR[category]
        names = [s["name"] for s in subs]
        overlaps.append({
            "category": category, "label": label, "count": len(subs), "names": names,
            "monthly_try": round(sum(finance.sub_monthly(s) for s in subs), 2),
            # Informational only — Subly never decides to cancel on the user's behalf.
            "message": f"{len(subs)} {label} aboneliğin bulunuyor: {', '.join(names)}.",
        })
    overlaps.sort(key=lambda o: -o["count"])

    unused = [s for s in active if s.get("usage") == "unused"]
    return {
        "active_count": len(active),
        "total_count": len(subscriptions),
        "monthly_total_try": monthly_total,
        "yearly_projection_try": round(monthly_total * 12, 2),
        "upcoming": upcoming,
        "next_renewal": upcoming[0] if upcoming else None,
        "unused_count": len(unused),
        "rarely_count": sum(1 for s in active if s.get("usage") == "rarely"),
        "unused_monthly_try": round(sum(finance.sub_monthly(s) for s in unused), 2),
        "by_category": _bucket(by_category),
        "by_payment_method": _bucket(by_method),
        "yearly_subscriptions": yearly,
        "price_changes": price_changes,
        "overlaps": overlaps,
        "legacy_unreviewed": sum(1 for s in subscriptions if not s.get("schema_version") and not s.get("legacy_reviewed_at")),
        "rates": dict(finance.RATES),
    }
