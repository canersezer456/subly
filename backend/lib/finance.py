"""Pure finance computations shared by the dashboard, savings, alerts, calendar and AI assistant."""

import asyncio
from calendar import monthrange
from datetime import date, timedelta

from lib.dates import today_iso
from lib.db import db

TZ = "Europe/Istanbul"
RATES = {"TRY": 1.0, "USD": 38.0, "EUR": 41.0}  # approximate, for aggregating mixed-currency subscriptions
MONTHS_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
FREQ_MONTHS = {"monthly": 1, "bimonthly": 2, "quarterly": 3, "yearly": 12}


def today() -> date:
    return date.fromisoformat(today_iso(TZ))


def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def month_label(key: str) -> str:
    y, m = key.split("-")
    return f"{MONTHS_TR[int(m) - 1]} {y}"


def month_bounds(key: str) -> tuple[date, date]:
    y, m = (int(part) for part in key.split("-"))
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def shift_month(key: str, n: int) -> str:
    return month_key(add_months(month_bounds(key)[0], n))


def tl(amount: float) -> str:
    return "₺" + f"{amount:,.0f}".replace(",", ".")


def to_try(amount: float, currency: str) -> float:
    return round(amount * RATES.get(currency, 1.0), 2)


def parse(value: str) -> date:
    return date.fromisoformat(value[:10])


def next_occurrence(anchor: date, frequency: str, floor: date, strict: bool = False) -> date | None:
    """First occurrence of a recurring date on/after `floor` (after, if strict). None for a past one-off."""
    step = FREQ_MONTHS.get(frequency)
    if step is None:  # once
        if anchor > floor or (anchor == floor and not strict):
            return anchor
        return None
    current = anchor
    while current < floor or (strict and current == floor):
        current = add_months(current, step)
    return current


def sub_monthly(sub: dict) -> float:
    price = to_try(sub.get("price", 0), sub.get("currency", "TRY"))
    return round(price / 12, 2) if sub.get("billing_cycle") == "yearly" else price


def sub_next_renewal(sub: dict, floor: date) -> date:
    step = "yearly" if sub.get("billing_cycle") == "yearly" else "monthly"
    return next_occurrence(parse(sub["renewal_date"]), step, floor) or floor


async def load_user_data(user_id: str) -> dict:
    q = {"user_id": user_id}
    incomes, expenses, bills, budgets, subscriptions = await asyncio.gather(
        db.incomes.find(q, {"_id": 0}).to_list(2000),
        db.expenses.find(q, {"_id": 0}).to_list(5000),
        db.bills.find(q, {"_id": 0}).to_list(1000),
        db.budgets.find(q, {"_id": 0}).to_list(500),
        db.subscriptions.find(q, {"_id": 0}).to_list(500),
    )
    return {"incomes": incomes, "expenses": expenses, "bills": bills, "budgets": budgets, "subscriptions": subscriptions}


def in_month(value: str, key: str) -> bool:
    return value[:7] == key


def income_for_month(incomes: list[dict], key: str) -> float:
    total = 0.0
    for inc in incomes:
        if inc.get("kind") == "regular" and inc["date"][:7] <= key:
            total += inc["amount"]
        elif inc.get("kind") != "regular" and in_month(inc["date"], key):
            total += inc["amount"]
    return round(total, 2)


def bills_for_month(bills: list[dict], key: str) -> list[tuple[dict, date]]:
    """Bills falling due inside `key`, projecting recurring ones onto that month."""
    start, end = month_bounds(key)
    result = []
    for bill in bills:
        anchor = parse(bill["due_date"])
        occurrence = next_occurrence(anchor, bill.get("frequency", "monthly"), start) if anchor < start else anchor
        if occurrence and start <= occurrence <= end:
            result.append((bill, occurrence))
    return result


def active_subs(subs: list[dict]) -> list[dict]:
    return [s for s in subs if s.get("status") != "cancelled"]


def category_breakdown(data: dict, key: str) -> list[dict]:
    totals: dict[str, float] = {}
    for exp in data["expenses"]:
        if in_month(exp["date"], key):
            totals[exp["category"]] = totals.get(exp["category"], 0) + exp["amount"]
    bills_total = sum(b["amount"] for b, _ in bills_for_month(data["bills"], key))
    if bills_total:
        totals["Faturalar"] = totals.get("Faturalar", 0) + bills_total
    subs_total = sum(sub_monthly(s) for s in active_subs(data["subscriptions"]))
    if subs_total:
        totals["Abonelikler"] = totals.get("Abonelikler", 0) + subs_total
    grand = sum(totals.values()) or 1
    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return [{"category": c, "amount": round(a, 2), "percent": round(a / grand * 100, 1)} for c, a in ordered]


def expense_for_month(data: dict, key: str) -> float:
    return round(sum(item["amount"] for item in category_breakdown(data, key)), 2)


def upcoming_payments(data: dict, ref: date, horizon_days: int = 30) -> list[dict]:
    items = []
    limit = ref + timedelta(days=horizon_days)
    for bill in data["bills"]:
        anchor = parse(bill["due_date"])
        paid = bill.get("status") == "paid"
        nxt = next_occurrence(anchor, bill.get("frequency", "monthly"), ref, strict=paid)
        if nxt and nxt <= limit:
            items.append({"id": bill["id"], "title": bill["provider"], "amount": bill["amount"], "currency": "TRY", "date": nxt.isoformat(), "days_until": (nxt - ref).days, "kind": "bill", "category": bill["bill_type"], "status": "paid" if paid and nxt == anchor else "pending"})
    for sub in active_subs(data["subscriptions"]):
        nxt = sub_next_renewal(sub, ref)
        if nxt <= limit:
            items.append({"id": sub["id"], "title": sub["name"], "amount": sub["price"], "currency": sub.get("currency", "TRY"), "date": nxt.isoformat(), "days_until": (nxt - ref).days, "kind": "subscription", "category": sub.get("category", "Abonelik"), "status": "active"})
    return sorted(items, key=lambda i: (i["date"], -i["amount"]))


def budget_usage(data: dict, key: str) -> list[dict]:
    breakdown = {c["category"]: c["amount"] for c in category_breakdown(data, key)}
    usage = []
    for budget in data["budgets"]:
        if budget.get("month") and budget["month"] != key:
            continue
        spent = breakdown.get(budget["category"], 0.0)
        percent = round(spent / budget["limit"] * 100, 1) if budget["limit"] else 0
        usage.append({"id": budget["id"], "category": budget["category"], "limit": budget["limit"], "spent": round(spent, 2), "percent": percent, "exceeded": spent > budget["limit"], "month": key})
    return sorted(usage, key=lambda u: u["percent"], reverse=True)


def savings_insights(data: dict, key: str) -> list[dict]:
    insights = []
    for sub in active_subs(data["subscriptions"]):
        usage = sub.get("usage", "active")
        if usage == "unused":
            insights.append({"id": f"unused-{sub['id']}", "level": "red", "title": f"Kullanılmayan abonelik: {sub['name']}", "detail": "Bu servisi kullanmadığını işaretledin. İptal edersen aylık bu tutarı geri kazanırsın.", "amount": sub_monthly(sub), "action_label": "Aboneliğe git", "action_path": "/subscriptions"})
        elif usage == "rarely":
            insights.append({"id": f"rare-{sub['id']}", "level": "yellow", "title": f"Nadiren kullanılan: {sub['name']}", "detail": "Daha düşük bir plana geçmeyi veya duraklatmayı değerlendir.", "amount": round(sub_monthly(sub) * 0.5, 2), "action_label": "Planları karşılaştır", "action_path": "/subscriptions?tab=deals"})
    for usage in budget_usage(data, key):
        if usage["exceeded"]:
            insights.append({"id": f"budget-{usage['id']}", "level": "yellow", "title": f"Bütçe aşımı: {usage['category']}", "detail": f"Bu ay {usage['category']} bütçen aşıldı. Kalan günlerde bu kategoriyi frenlemek fark yaratır.", "amount": round(usage["spent"] - usage["limit"], 2), "action_label": "Bütçeyi incele", "action_path": "/budget"})
    for bill in data["bills"]:
        history = sorted([b for b in data["bills"] if b["provider"] == bill["provider"] and b["id"] != bill["id"] and b["due_date"] < bill["due_date"]], key=lambda b: b["due_date"])
        if history and in_month(bill["due_date"], key):
            prev = history[-1]["amount"]
            if prev and bill["amount"] > prev * 1.2:
                insights.append({"id": f"bill-{bill['id']}", "level": "yellow", "title": f"Yüksek fatura: {bill['provider']}", "detail": f"Önceki döneme göre %{round((bill['amount'] / prev - 1) * 100)} artış var. Tarife veya tüketimini kontrol et.", "amount": round(bill["amount"] - prev, 2), "action_label": "Faturayı gör", "action_path": "/bills"})
    for sub in active_subs(data["subscriptions"]):
        if sub.get("billing_cycle", "monthly") == "monthly" and sub_monthly(sub) >= 50 and sub.get("usage", "active") == "active":
            insights.append({"id": f"yearly-{sub['id']}", "level": "green", "title": f"Yıllık plan alternatifi: {sub['name']}", "detail": "Sağlayıcılar yıllık ödemede genelle %15-20 indirim uygular. Bu servisi düzenli kullanıyorsan yıllık plana geçmeyi değerlendir.", "amount": round(sub_monthly(sub) * 0.16, 2), "action_label": "Fırsatları gör", "action_path": "/subscriptions?tab=deals"})
    return insights


def alerts(data: dict, ref: date, key: str) -> list[dict]:
    out = []
    for item in upcoming_payments(data, ref, 3):
        when = "bugün" if item["days_until"] == 0 else f"{item['days_until']} gün sonra"
        verb = "yenileniyor" if item["kind"] == "subscription" else "son ödeme"
        out.append({"id": f"due-{item['id']}", "level": "warning" if item["days_until"] <= 1 else "info", "message": f"{item['title']} — {tl(item['amount'])} {when} {verb}.", "path": "/calendar"})
    for usage in budget_usage(data, key):
        if usage["exceeded"]:
            out.append({"id": f"over-{usage['id']}", "level": "warning", "message": f"{usage['category']} bütçen aşıldı (%{usage['percent']:.0f}).", "path": "/budget"})
        elif usage["percent"] >= 85:
            out.append({"id": f"near-{usage['id']}", "level": "info", "message": f"{usage['category']} harcaman bütçenin %{usage['percent']:.0f}'ine ulaştı.", "path": "/budget"})
    unused = [s for s in active_subs(data["subscriptions"]) if s.get("usage") == "unused"]
    if unused:
        out.append({"id": "unused-subs", "level": "info", "message": f"Kullanmadığın {len(unused)} abonelik tespit edildi.", "path": "/savings"})
    this_m, last_m = expense_for_month(data, key), expense_for_month(data, shift_month(key, -1))
    if last_m and this_m > last_m * 1.1:
        out.append({"id": "spend-up", "level": "warning", "message": f"Bu ay harcaman geçen aya göre {tl(this_m - last_m)} arttı.", "path": "/expenses"})
    potential = sum(i["amount"] for i in savings_insights(data, key))
    if potential > 0:
        out.append({"id": "potential", "level": "success", "message": f"Bu ay tahmini {tl(potential)} tasarruf edebilirsin.", "path": "/savings"})
    return out


def summary(data: dict, ref: date) -> dict:
    key = month_key(ref)
    income_total = income_for_month(data["incomes"], key)
    expense_total = expense_for_month(data, key)
    last_month = expense_for_month(data, shift_month(key, -1))
    subs = active_subs(data["subscriptions"])
    monthly_subs = round(sum(sub_monthly(s) for s in subs), 2)
    trend = []
    for offset in range(-5, 1):
        k = shift_month(key, offset)
        trend.append({"month": k, "label": MONTHS_TR[int(k[5:]) - 1][:3], "expense": expense_for_month(data, k), "income": income_for_month(data["incomes"], k)})
    remaining = round(income_total - expense_total, 2)
    return {
        "month": key,
        "month_label": month_label(key),
        "today": ref.isoformat(),
        "income_total": income_total,
        "expense_total": expense_total,
        "remaining": remaining,
        "savings_rate": round(remaining / income_total * 100, 1) if income_total else 0.0,
        "last_month_expense": last_month,
        "expense_change_percent": round((expense_total / last_month - 1) * 100, 1) if last_month else 0.0,
        "subscription_monthly": monthly_subs,
        "subscription_yearly": round(monthly_subs * 12, 2),
        "bills_total": round(sum(b["amount"] for b, _ in bills_for_month(data["bills"], key)), 2),
        "upcoming": upcoming_payments(data, ref),
        "categories": category_breakdown(data, key),
        "budgets": budget_usage(data, key),
        "trend": trend,
        "potential_savings": round(sum(i["amount"] for i in savings_insights(data, key)), 2),
        "alerts_count": len(alerts(data, ref, key)),
    }


def calendar(data: dict, key: str) -> dict:
    start, end = month_bounds(key)
    events = []
    for bill, occurrence in bills_for_month(data["bills"], key):
        events.append({"id": bill["id"], "date": occurrence.isoformat(), "title": bill["provider"], "amount": bill["amount"], "currency": "TRY", "kind": "bill", "category": bill["bill_type"], "status": bill.get("status", "pending") if occurrence.isoformat() == bill["due_date"] else "pending"})
    for sub in active_subs(data["subscriptions"]):
        anchor = parse(sub["renewal_date"])
        step = "yearly" if sub.get("billing_cycle") == "yearly" else "monthly"
        occurrence = next_occurrence(anchor, step, start) if anchor < start else anchor
        if occurrence and start <= occurrence <= end:
            events.append({"id": sub["id"], "date": occurrence.isoformat(), "title": sub["name"], "amount": sub["price"], "currency": sub.get("currency", "TRY"), "kind": "subscription", "category": sub.get("category", "Abonelik"), "status": "active"})
    for inc in data["incomes"]:
        anchor = parse(inc["date"])
        if inc.get("kind") == "regular":
            occurrence = next_occurrence(anchor, "monthly", start) if anchor < start else anchor
        else:
            occurrence = anchor
        if occurrence and start <= occurrence <= end:
            events.append({"id": inc["id"], "date": occurrence.isoformat(), "title": inc["source"], "amount": inc["amount"], "currency": "TRY", "kind": "income", "category": inc.get("kind", "regular"), "status": "expected"})
    events.sort(key=lambda e: e["date"])
    return {
        "month": key,
        "label": month_label(key),
        "total_out": round(sum(to_try(e["amount"], e["currency"]) for e in events if e["kind"] != "income"), 2),
        "total_in": round(sum(e["amount"] for e in events if e["kind"] == "income"), 2),
        "events": events,
    }
