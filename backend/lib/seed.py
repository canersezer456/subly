"""Starter data. Subscriptions are seeded for every new account; the richer finance sample only for the demo account."""

import uuid
from datetime import datetime, timedelta, timezone

from lib.db import db
from lib.finance import add_months, today

DEMO_EMAIL = "demo@subly.app"


def _doc(user_id: str, **fields) -> dict:
    return {"id": str(uuid.uuid4()), "user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat(), **fields}


async def seed_starter_subscriptions(user_id: str) -> None:
    if await db.subscriptions.count_documents({"user_id": user_id}):
        return
    t = today()
    d = lambda days: (t + timedelta(days=days)).isoformat()  # noqa: E731
    starter = [
        _doc(user_id, name="Netflix", category="Eğlence", price=229.99, currency="TRY", renewal_date=d(2), payment_method="Kart •••• 4821", cancellation_url="https://www.netflix.com/cancelplan", source="manual", status="active", billing_cycle="monthly", usage="active"),
        _doc(user_id, name="Spotify", category="Müzik", price=99.99, currency="TRY", renewal_date=d(9), payment_method="Kart •••• 4821", cancellation_url="https://www.spotify.com/account/subscription/", source="manual", status="active", billing_cycle="monthly", usage="rarely"),
        _doc(user_id, name="YouTube Premium", category="Eğlence", price=79.99, currency="TRY", renewal_date=d(14), payment_method="Kart •••• 4821", cancellation_url="https://www.youtube.com/paid_memberships", source="mock_scan", status="active", billing_cycle="monthly", usage="active"),
        _doc(user_id, name="Google One", category="Bulut", price=399, currency="TRY", renewal_date=d(19), payment_method="Kart •••• 1190", cancellation_url="https://one.google.com/settings", source="manual", status="active", billing_cycle="monthly", usage="unused"),
    ]
    await db.subscriptions.insert_many(starter)


async def seed_demo_finance(user_id: str) -> None:
    if await db.incomes.count_documents({"user_id": user_id}):
        return
    t = today()
    first = t.replace(day=1)
    prev = add_months(first, -1)
    prev2 = add_months(first, -2)
    d = lambda days: (t + timedelta(days=days)).isoformat()  # noqa: E731

    incomes = [
        _doc(user_id, source="Maaş", amount=40000, kind="regular", date=prev2.replace(day=min(15, 28)).isoformat(), note="Aylık net maaş"),
        _doc(user_id, source="Freelance", amount=5000, kind="extra", date=first.replace(day=min(t.day, 28)).isoformat(), note="Tasarım projesi"),
        _doc(user_id, source="Ek gelir", amount=2000, kind="one_time", date=d(-3), note="İkinci el satış"),
    ]
    expenses = []
    plan = [
        ("Market", "Migros", 1840), ("Market", "Haftalık pazar", 1200), ("Market", "CarrefourSA", 2100), ("Market", "Kasap", 1100),
        ("Restoran", "Öğle yemekleri", 1450), ("Restoran", "Hafta sonu kahvaltı", 900),
        ("Ulaşım", "İstanbulkart", 1250), ("Ulaşım", "Taksi", 850),
        ("Alışveriş", "Kıyafet", 1900), ("Eğlence", "Sinema", 650), ("Eğlence", "Konser bileti", 1200),
        ("Sağlık", "Eczane", 480), ("Eğitim", "Online kurs", 750), ("Ev", "Temizlik malzemesi", 620),
    ]
    for index, (category, title, amount) in enumerate(plan):
        day_offset = -min(index * 2, max(t.day - 1, 0))
        expenses.append(_doc(user_id, title=title, amount=amount, category=category, date=d(day_offset), payment_method="Kart •••• 4821" if index % 3 else "Nakit", note=""))
    for category, title, amount in [("Market", "Market alışverişi", 5600), ("Restoran", "Dışarıda yemek", 2100), ("Ulaşım", "Ulaşım", 1900), ("Eğlence", "Eğlence", 1500), ("Alışveriş", "Alışveriş", 2400), ("Sağlık", "Sağlık", 300)]:
        expenses.append(_doc(user_id, title=title, amount=amount, category=category, date=prev.replace(day=12).isoformat(), payment_method="Kart •••• 4821", note="Geçen ay özeti"))
    for category, title, amount in [("Market", "Market alışverişi", 5200), ("Restoran", "Dışarıda yemek", 1800), ("Ulaşım", "Ulaşım", 1700), ("Eğlence", "Eğlence", 900)]:
        expenses.append(_doc(user_id, title=title, amount=amount, category=category, date=prev2.replace(day=12).isoformat(), payment_method="Kart •••• 4821", note="Önceki ay özeti"))

    bills = [
        _doc(user_id, provider="Elektrik (CK Boğaziçi)", bill_type="Elektrik", amount=642, due_date=d(0), frequency="monthly", auto_pay=False, payment_method="Havale / EFT", bill_number="EL-2049-118", note="", status="pending"),
        _doc(user_id, provider="Elektrik (CK Boğaziçi)", bill_type="Elektrik", amount=498, due_date=add_months(t, -1).isoformat(), frequency="once", auto_pay=False, payment_method="Havale / EFT", bill_number="EL-2049-093", note="Geçen ay", status="paid"),
        _doc(user_id, provider="Türk Telekom İnternet", bill_type="İnternet", amount=549, due_date=d(5), frequency="monthly", auto_pay=True, payment_method="Kart •••• 4821", bill_number="TT-77120", note="", status="pending"),
        _doc(user_id, provider="Vodafone", bill_type="Telefon", amount=420, due_date=d(8), frequency="monthly", auto_pay=True, payment_method="Kart •••• 4821", bill_number="", note="", status="pending"),
        _doc(user_id, provider="Kira", bill_type="Kira", amount=18000, due_date=d(12), frequency="monthly", auto_pay=False, payment_method="Havale / EFT", bill_number="", note="Ev sahibi IBAN", status="pending"),
        _doc(user_id, provider="İSKİ Su", bill_type="Su", amount=310, due_date=d(16), frequency="monthly", auto_pay=False, payment_method="Havale / EFT", bill_number="", note="", status="pending"),
        _doc(user_id, provider="İGDAŞ Doğalgaz", bill_type="Doğalgaz", amount=890, due_date=d(21), frequency="monthly", auto_pay=False, payment_method="Havale / EFT", bill_number="", note="", status="pending"),
    ]
    budgets = [
        _doc(user_id, category="Market", limit=7000, month=""),
        _doc(user_id, category="Ulaşım", limit=2500, month=""),
        _doc(user_id, category="Eğlence", limit=1500, month=""),
        _doc(user_id, category="Abonelikler", limit=1500, month=""),
        _doc(user_id, category="Restoran", limit=3000, month=""),
    ]
    await db.incomes.insert_many(incomes)
    await db.expenses.insert_many(expenses)
    await db.bills.insert_many(bills)
    await db.budgets.insert_many(budgets)
