"""Financial-transaction discovery: source interface, merchant normalization and
recurring-payment detection.

`BankFeedAdapter` is the hook for a future card/bank aggregator. No aggregator is
integrated: there is no licensed open-banking provider (in Türkiye a BDDK-licensed
payment/e-money institution with ÖHVPS/account-information access, or an AIS provider
such as Tink/TrueLayer/Plaid elsewhere) wired in, so it always reports "not integrated"
and never returns (let alone invents) transactions. Setting environment variables does
not change that; a real integration is code + a provider contract.
`detect_recurring` is source-agnostic: today it is fed by the user's own pasted
statement (lib/discovery/importer.py); a bank feed would feed it the same way.

Privacy: drafts keep the *normalized* merchant pattern ("NETFLIX"), a count, the
cadence and dates — not raw descriptors (which can contain card digits, locations
or reference numbers).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median
from typing import Protocol

from lib import provider_catalog

class TransactionSourceNotConnected(RuntimeError):
    pass


@dataclass(frozen=True)
class Transaction:
    date: date
    description: str
    amount: float  # positive = money out
    currency: str = "TRY"


class TransactionSource(Protocol):
    id: str
    name: str

    def is_configured(self) -> bool: ...

    async def fetch_transactions(self, user_id: str, since: date) -> list[Transaction]: ...


class BankFeedAdapter:
    """Placeholder for an open-banking / card aggregator (consent-based, read-only)."""

    id = "bank_feed"
    name = "Banka / kart bağlantısı"

    def is_configured(self) -> bool:
        return False  # no provider integration exists yet (see module docstring)

    async def fetch_transactions(self, user_id: str, since: date) -> list[Transaction]:
        raise TransactionSourceNotConnected("Banka/kart bağlantısı yapılandırılmadı")


TRANSACTION_ADAPTERS = [BankFeedAdapter()]

# (cycle, min_days, max_days)
CADENCES = [("monthly", 26, 35), ("quarterly", 84, 98), ("yearly", 350, 380)]
CYCLE_DAYS = {"monthly": 30, "quarterly": 91, "yearly": 365}


def status() -> dict:
    adapters = [{"id": a.id, "name": a.name, "configured": a.is_configured(), "connected": False, "state": "not_integrated"} for a in TRANSACTION_ADAPTERS]
    return {"available": False, "connected": False, "state": "not_integrated", "adapters": adapters}


def _cadence(dates: list[date]) -> str | None:
    unique = sorted(set(dates))
    if len(unique) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(unique, unique[1:])]
    typical = median(gaps)
    for cycle, low, high in CADENCES:
        if low <= typical <= high and all(low - 5 <= g <= high + 5 for g in gaps):
            return cycle
    return None


def _add_cycle(d: date, cycle: str) -> date:
    from lib.finance import add_months  # local import: finance imports db at module load

    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[cycle]
    return add_months(d, months)


def detect_recurring(transactions: list[Transaction], *, evidence_type: str, evidence_source: str, today: date | None = None) -> list[dict]:
    """Group debits by normalized merchant and turn each group into a candidate draft.

    Rules (deliberately conservative):
    - unknown merchants are ignored — Subly does not guess subscriptions from arbitrary shops;
    - ambiguous merchants (APPLE.COM/BILL, GOOGLE, AMAZON, MICROSOFT…) produce a
      low-confidence draft with no provider chosen, listing the possibilities;
    - confidence rises with a regular cadence and a stable amount, never above 0.9
      from a single source.
    """
    groups: dict[tuple, dict] = {}
    for tx in transactions:
        if tx.amount == 0:
            continue
        match = provider_catalog.match_merchant(tx.description)
        if match["kind"] == "unknown":
            continue
        key = (match["kind"], tuple(match["provider_ids"]), tx.currency)
        group = groups.setdefault(key, {"match": match, "currency": tx.currency, "items": []})
        group["items"].append(tx)

    drafts: list[dict] = []
    for (kind, provider_ids, currency), group in groups.items():
        items = sorted(group["items"], key=lambda t: t.date)
        dates = [t.date for t in items]
        amounts = [abs(t.amount) for t in items]
        cycle = _cadence(dates)
        stable = max(amounts) <= min(amounts) * 1.25
        last = items[-1]
        count = len(set(dates))

        # One descriptor naming different products (e.g. GITHUB: GitHub or GitHub Copilot)
        # is ambiguous too; plans of one product (OPENAI: ChatGPT Plus / Pro) are not.
        if kind == "provider" and not provider_catalog.same_family(list(provider_ids)):
            kind = "ambiguous"
        if kind == "ambiguous":
            confidence = 0.25
        else:
            confidence = 0.45
            if cycle:
                confidence += 0.25
                if count >= 3:
                    confidence += 0.1
            if stable and count >= 2:
                confidence += 0.05
            if len(provider_ids) > 1:
                confidence -= 0.1  # e.g. OPENAI: Plus or Pro? the user has to say which
            store = any((provider_catalog.get_provider(pid) or {}).get("one_off_purchases") for pid in provider_ids)
            if store and not cycle:
                confidence -= 0.15  # PlayStation/Xbox/Nintendo/EA descriptors also bill one-off store purchases
        confidence = round(min(confidence, 0.9), 2)

        renewal = None
        if cycle:
            renewal = _add_cycle(last.date, cycle)
            ref = today or date.today()
            while renewal < ref:
                renewal = _add_cycle(renewal, cycle)

        providers = [provider_catalog.get_provider(pid) for pid in provider_ids]
        providers = [p for p in providers if p]
        primary = providers[0] if kind == "provider" and providers else None
        cadence_label = {"monthly": "aylık", "quarterly": "3 aylık", "yearly": "yıllık"}.get(cycle or "", "düzensiz/tek")
        drafts.append({
            "provider_id": primary["id"] if primary else None,
            "provider_name": primary["name"] if primary else group["match"].get("label") or " / ".join(p["name"] for p in providers) or "Bilinmeyen servis",
            "alternatives": [p["id"] for p in providers if not primary or p["id"] != primary["id"]],
            "ambiguous": kind == "ambiguous",
            "suggested_plan": primary["plans"][0] if primary and len(primary["plans"]) == 1 else None,
            "suggested_price": round(abs(last.amount), 2),
            "currency": currency,
            "billing_cycle": cycle,
            "renewal_date": renewal.isoformat() if renewal else None,
            "confidence": confidence,
            "evidence": [{
                "type": evidence_type,
                "source": evidence_source,
                "merchant": group["match"]["matched"],
                "count": count,
                "cadence": cycle,
                "summary": f"{group['match']['matched']} · {count} ödeme · {cadence_label}",
                "first_seen": dates[0].isoformat(),
                "observed_at": last.date.isoformat(),
            }],
        })
    drafts.sort(key=lambda d: (-d["confidence"], d["provider_name"]))
    return drafts


def lookback_floor(today: date, days: int = 400) -> date:
    return today - timedelta(days=days)
