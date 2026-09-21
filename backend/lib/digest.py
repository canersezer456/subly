"""Weekly summary email: template builder + lightweight in-process scheduler."""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from lib import finance
from lib.db import db
from lib.email import EMAIL_FROM_NAME, send_email

logger = logging.getLogger(__name__)
TZ = ZoneInfo(finance.TZ)
WEEKDAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
DEFAULT_PREFS = {"enabled": False, "weekday": 0, "hour": 9, "origin": "", "last_sent_at": None, "reminders_enabled": False, "reminder_hour": 8, "last_reminder_date": None}


async def get_prefs(user_id: str) -> dict:
    doc = await db.digest_prefs.find_one({"user_id": user_id}, {"_id": 0, "user_id": 0}) or {}
    return {**DEFAULT_PREFS, **doc}


def _money(value: float, currency: str = "TRY") -> str:
    symbol = {"TRY": "₺", "USD": "$", "EUR": "€"}.get(currency, currency + " ")
    return symbol + f"{value:,.0f}".replace(",", ".")


def build_digest(user: dict, data: dict, origin: str) -> tuple[str, str]:
    """Returns (subject, html). Fixed server-side template; every interpolation is escaped."""
    ref = finance.today()
    key = finance.month_key(ref)
    summary = finance.summary(data, ref)
    upcoming = finance.upcoming_payments(data, ref, 7)
    insights = finance.savings_insights(data, key)
    order = {"red": 0, "yellow": 1, "green": 2}
    insights.sort(key=lambda i: (order.get(i["level"], 9), -i["amount"]))
    week_total = sum(finance.to_try(u["amount"], u["currency"]) for u in upcoming)
    name = escape(user.get("name", "").split(" ")[0] or "Merhaba")
    app_link = origin.rstrip("/") if origin.startswith("https://") else ""

    def row(label: str, value: str, color: str = "#0f172a") -> str:
        return (f'<tr><td style="padding:8px 0;color:#64748b;font-size:13px">{label}</td>'
                f'<td align="right" style="padding:8px 0;font-weight:700;font-size:14px;color:{color}">{value}</td></tr>')

    upcoming_rows = "".join(
        row(f"{escape(u['title'])} <span style=\"color:#94a3b8\">· {finance.parse(u['date']).strftime('%d.%m')}"
            f" · {'bugün' if u['days_until'] == 0 else str(u['days_until']) + ' gün sonra'}</span>", _money(u["amount"], u["currency"]))
        for u in upcoming
    ) or '<tr><td style="padding:8px 0;color:#64748b;font-size:13px">Bu hafta planlı ödeme görünmüyor.</td></tr>'

    dot = {"red": "#ef4444", "yellow": "#f59e0b", "green": "#10b981"}
    tips = "".join(
        f'<tr><td style="padding:8px 0;font-size:13px;color:#0f172a">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:99px;background:{dot[i["level"]]};margin-right:8px"></span>'
        f'{escape(i["title"])}<div style="color:#64748b;font-size:12px;margin:2px 0 0 16px">{escape(i["detail"])}</div></td>'
        f'<td align="right" valign="top" style="padding:8px 0;font-weight:700;font-size:13px;color:#059669">{_money(i["amount"])}</td></tr>'
        for i in insights[:3]
    ) or '<tr><td style="padding:8px 0;color:#64748b;font-size:13px">Şu an belirgin bir tasarruf fırsatı yok — böyle devam.</td></tr>'

    cta = (f'<p style="margin:24px 0 0"><a href="{escape(app_link + "/dashboard")}" style="display:inline-block;background:#10b981;color:#ffffff;'
           f'text-decoration:none;font-weight:700;font-size:14px;padding:12px 20px;border-radius:10px">Panelini aç</a></p>') if app_link else ""
    settings_note = (f' Bu e-postayı Subly uygulamasındaki <a href="{escape(app_link + "/settings")}" style="color:#64748b">Ayarlar</a> sayfasından kapatabilirsin.') if app_link else ""

    subject = f"Haftalık özet · bu hafta {_money(week_total)} ödemen var"
    html = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f5f0;padding:24px 0;font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;padding:32px;border:1px solid #e7e5df">
<tr><td>
  <p style="margin:0;font-size:11px;letter-spacing:.18em;color:#10b981;font-weight:700">{escape(EMAIL_FROM_NAME).upper()} · HAFTALIK ÖZET</p>
  <h1 style="margin:8px 0 4px;font-size:22px;color:#0f172a">Merhaba {name} 👋</h1>
  <p style="margin:0 0 20px;font-size:14px;color:#64748b">{escape(summary['month_label'])} için kısa bir finansal durum özeti.</p>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #eef0f3;border-bottom:1px solid #eef0f3">
    {row("Bu ay gelir", _money(summary['income_total']), "#059669")}
    {row("Bu ay gider (fatura + abonelik dahil)", _money(summary['expense_total']), "#dc2626")}
    {row("Kalan", _money(summary['remaining']), "#0f172a" if summary['remaining'] >= 0 else "#dc2626")}
  </table>

  <h2 style="margin:24px 0 6px;font-size:15px;color:#0f172a">📅 Önümüzdeki 7 gün · {_money(week_total)}</h2>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{upcoming_rows}</table>

  <h2 style="margin:24px 0 6px;font-size:15px;color:#0f172a">💡 Tasarruf ipuçları · potansiyel {_money(summary['potential_savings'])}/ay</h2>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{tips}</table>
  {cta}
  <p style="margin:28px 0 0;font-size:11px;line-height:1.6;color:#94a3b8">Bu e-posta {escape(EMAIL_FROM_NAME)} tarafından, senin kayıtlı verilerine dayanarak otomatik oluşturuldu. Asla şifre, kart bilgisi veya doğrulama kodu istemeyiz.{settings_note}</p>
</td></tr></table>
</td></tr></table>"""
    return subject, html


async def send_digest(user: dict, origin: str) -> str | None:
    data = await finance.load_user_data(user["user_id"])
    subject, html = build_digest(user, data, origin)
    email_id = await send_email(to=user["email"], subject=subject, html=html)
    await db.digest_prefs.update_one({"user_id": user["user_id"]}, {"$set": {"last_sent_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return email_id


def due_today(data: dict) -> list[dict]:
    """Bills and subscription renewals whose payment date is today (Istanbul)."""
    return [u for u in finance.upcoming_payments(data, finance.today(), 0) if u["days_until"] == 0 and u["status"] != "paid"]


def build_reminder(user: dict, items: list[dict], origin: str) -> tuple[str, str]:
    """Same-day reminder. Fixed server-side template; everything interpolated is escaped."""
    name = escape(user.get("name", "").split(" ")[0] or "Merhaba")
    app_link = origin.rstrip("/") if origin.startswith("https://") else ""
    total = sum(finance.to_try(i["amount"], i["currency"]) for i in items)
    today_label = finance.today().strftime("%d.%m.%Y")
    rows = "".join(
        f'<tr><td style="padding:10px 0;border-bottom:1px solid #eef0f3;font-size:14px;color:#0f172a">'
        f'{"🔄" if i["kind"] == "subscription" else "🧾"} <strong>{escape(i["title"])}</strong>'
        f'<div style="color:#64748b;font-size:12px;margin-top:2px">{escape(i["category"])} · {"abonelik yenilemesi" if i["kind"] == "subscription" else "fatura son ödeme günü"}</div></td>'
        f'<td align="right" valign="top" style="padding:10px 0;border-bottom:1px solid #eef0f3;font-weight:700;font-size:15px;color:#0f172a">{_money(i["amount"], i["currency"])}</td></tr>'
        for i in items
    )
    cta = (f'<p style="margin:24px 0 0"><a href="{escape(app_link + "/bills")}" style="display:inline-block;background:#10b981;color:#ffffff;text-decoration:none;'
           f'font-weight:700;font-size:14px;padding:12px 20px;border-radius:10px">Ödendi olarak işaretle</a>'
           f' <a href="{escape(app_link + "/calendar")}" style="display:inline-block;margin-left:8px;color:#0f172a;text-decoration:none;font-weight:700;font-size:14px;padding:12px 20px;border-radius:10px;border:1px solid #e2e8f0">Takvimi aç</a></p>') if app_link else ""
    settings_note = (f' Hatırlatmaları <a href="{escape(app_link + "/settings")}" style="color:#64748b">Ayarlar</a> sayfasından kapatabilirsin.') if app_link else ""
    subject = f"Bugün {len(items)} ödemen var · {_money(total)}"
    html = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f5f0;padding:24px 0;font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;padding:32px;border:1px solid #e7e5df">
<tr><td>
  <p style="margin:0;font-size:11px;letter-spacing:.18em;color:#f59e0b;font-weight:700">{escape(EMAIL_FROM_NAME).upper()} · ÖDEME GÜNÜ</p>
  <h1 style="margin:8px 0 4px;font-size:22px;color:#0f172a">Günaydın {name} ☀️</h1>
  <p style="margin:0 0 16px;font-size:14px;color:#64748b">{today_label} · bugün vadesi gelen ödemelerin toplamı <strong style="color:#0f172a">{_money(total)}</strong>.</p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
  {cta}
  <p style="margin:28px 0 0;font-size:11px;line-height:1.6;color:#94a3b8">Bu hatırlatma {escape(EMAIL_FROM_NAME)} tarafından kayıtlı ödeme tarihlerine göre otomatik oluşturuldu. Asla şifre, kart bilgisi veya doğrulama kodu istemeyiz.{settings_note}</p>
</td></tr></table>
</td></tr></table>"""
    return subject, html


async def send_reminder(user: dict, origin: str) -> tuple[str | None, int]:
    """Returns (email_id, item_count); nothing is sent when nothing is due today."""
    data = await finance.load_user_data(user["user_id"])
    items = due_today(data)
    if not items:
        return None, 0
    subject, html = build_reminder(user, items, origin)
    email_id = await send_email(to=user["email"], subject=subject, html=html)
    await db.digest_prefs.update_one({"user_id": user["user_id"]}, {"$set": {"last_reminder_date": finance.today().isoformat()}}, upsert=True)
    return email_id, len(items)


async def run_due_reminders() -> int:
    now = datetime.now(TZ)
    today = finance.today().isoformat()
    sent = 0
    cursor = db.digest_prefs.find({"reminders_enabled": True, "reminder_hour": now.hour}, {"_id": 0})
    async for prefs in cursor:
        if prefs.get("last_reminder_date") == today:
            continue
        user = await db.users.find_one({"user_id": prefs["user_id"]}, {"_id": 0})
        if not user:
            continue
        try:
            email_id, _ = await send_reminder(user, prefs.get("origin", ""))
            sent += bool(email_id)
        except Exception:
            logger.exception("due reminder failed for %s", prefs["user_id"])
    return sent


async def run_due_digests() -> int:
    """Send to every opted-in user whose weekday/hour matches now (Istanbul) and who hasn't been sent in the last 6 days."""
    now = datetime.now(TZ)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
    sent = 0
    cursor = db.digest_prefs.find({"enabled": True, "weekday": now.weekday(), "hour": now.hour}, {"_id": 0})
    async for prefs in cursor:
        if prefs.get("last_sent_at") and prefs["last_sent_at"] > cutoff:
            continue
        user = await db.users.find_one({"user_id": prefs["user_id"]}, {"_id": 0})
        if not user:
            continue
        try:
            await send_digest(user, prefs.get("origin", ""))
            sent += 1
        except Exception:  # one failing mailbox must not stop the others
            logger.exception("weekly digest failed for %s", prefs["user_id"])
    return sent


async def scheduler_loop(interval_seconds: int = 600) -> None:
    while True:
        try:
            await run_due_digests()
            await run_due_reminders()
            await run_due_watch_alerts()
        except Exception:
            logger.exception("digest scheduler tick failed")
        await asyncio.sleep(interval_seconds)


# ---- Gaming price-watch email alerts ------------------------------------


WATCH_COOLDOWN_HOURS = 24


def build_watch_alert(user: dict, watch: dict, product: dict, offer: dict, origin: str) -> tuple[str, str]:
    """Fixed server-side template for the "price hit target" alert."""
    name = escape(user.get("name", "").split(" ")[0] or "Merhaba")
    app_link = origin.rstrip("/") if origin.startswith("https://") else ""
    product_name = escape(product.get("name", "Ürün"))
    game_name = escape(product.get("game_name", ""))
    seller_name = escape(offer.get("seller_name", ""))
    current = float(offer["price_try"])
    target = float(watch["target_price_try"])
    savings = max(0.0, target - current)
    cta = (f'<p style="margin:24px 0 0"><a href="{escape(app_link)}/gaming/products/{escape(product["id"])}" '
           f'style="display:inline-block;background:#10b981;color:#ffffff;text-decoration:none;font-weight:700;'
           f'font-size:14px;padding:12px 20px;border-radius:10px">Ürün sayfasını aç</a></p>') if app_link else ""
    settings_note = (f' Fiyat takibini <a href="{escape(app_link + "/gaming")}" style="color:#64748b">Gaming</a> ekranından yönetebilirsin.') if app_link else ""
    subject = f"🎮 {product.get('game_name', '')} · {product.get('name', '')} hedef fiyata düştü"
    html = f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f5f0;padding:24px 0;font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;padding:32px;border:1px solid #e7e5df">
<tr><td>
  <p style="margin:0;font-size:11px;letter-spacing:.18em;color:#10b981;font-weight:700">{escape(EMAIL_FROM_NAME).upper()} · FIRSAT UYARISI</p>
  <h1 style="margin:8px 0 4px;font-size:22px;color:#0f172a">Merhaba {name} 🎯</h1>
  <p style="margin:0 0 16px;font-size:14px;color:#64748b">Takip listenizdeki <strong style="color:#0f172a">{product_name}</strong> ({game_name}) ürünü belirlediğin hedef fiyatın altına düştü.</p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #eef0f3;border-bottom:1px solid #eef0f3;margin:16px 0">
    <tr><td style="padding:10px 0;color:#64748b;font-size:13px">Şu anki fiyat</td>
        <td align="right" style="padding:10px 0;font-weight:700;font-size:16px;color:#059669">{_money(current)}</td></tr>
    <tr><td style="padding:10px 0;color:#64748b;font-size:13px">Hedef fiyatın</td>
        <td align="right" style="padding:10px 0;font-weight:700;font-size:14px;color:#0f172a">{_money(target)}</td></tr>
    <tr><td style="padding:10px 0;color:#64748b;font-size:13px">Satıcı</td>
        <td align="right" style="padding:10px 0;font-weight:700;font-size:14px;color:#0f172a">{seller_name}</td></tr>
    {"<tr><td style='padding:10px 0;color:#64748b;font-size:13px'>Tasarruf</td><td align='right' style='padding:10px 0;font-weight:700;font-size:14px;color:#059669'>" + _money(savings) + "</td></tr>" if savings > 0 else ""}
  </table>
  {cta}
  <p style="margin:28px 0 0;font-size:11px;line-height:1.6;color:#94a3b8">Bu bildirim {escape(EMAIL_FROM_NAME)} tarafından senin oluşturduğun fiyat takibi kuralına göre otomatik gönderildi. Asla şifre, kart bilgisi veya doğrulama kodu istemeyiz.{settings_note}</p>
</td></tr></table>
</td></tr></table>"""
    return subject, html


async def _watch_context(watch: dict) -> tuple[dict, dict] | None:
    """Return (product, best_offer) applied with the user's overrides, or None if the product/offers are gone."""
    from lib.gaming_catalog import apply_overrides, catalog
    overrides = await db.gaming_price_overrides.find({"user_id": watch["user_id"]}, {"_id": 0}).to_list(2000)
    cat = apply_overrides(catalog(), overrides)
    product = cat["products_by_id"].get(watch["product_id"])
    if not product:
        return None
    offers = cat["offers_by_product"].get(watch["product_id"], [])
    if not offers:
        return None
    return product, offers[0]


async def send_watch_alert_now(watch_id: str, user_id: str, force: bool = False) -> dict:
    """Send the watch alert email now if triggered + cooldown ok. Returns {email_id, sent, reason}."""
    watch = await db.gaming_watches.find_one({"id": watch_id, "user_id": user_id}, {"_id": 0})
    if not watch:
        return {"sent": False, "reason": "not_found"}
    if not watch.get("notify_email", True):
        return {"sent": False, "reason": "notify_email_off"}
    ctx = await _watch_context(watch)
    if not ctx:
        return {"sent": False, "reason": "product_missing"}
    product, best = ctx
    if best["price_try"] > watch["target_price_try"]:
        return {"sent": False, "reason": "not_triggered"}
    if not force and watch.get("last_notified_at"):
        try:
            last = datetime.fromisoformat(watch["last_notified_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last < timedelta(hours=WATCH_COOLDOWN_HOURS):
                return {"sent": False, "reason": "cooldown"}
        except ValueError:
            pass
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        return {"sent": False, "reason": "user_missing"}
    prefs = await db.digest_prefs.find_one({"user_id": user_id}, {"_id": 0}) or {}
    origin = prefs.get("origin", "")
    subject, html = build_watch_alert(user, watch, product, best, origin)
    email_id = await send_email(to=user["email"], subject=subject, html=html)
    await db.gaming_watches.update_one({"id": watch_id, "user_id": user_id}, {"$set": {"last_notified_at": datetime.now(timezone.utc).isoformat()}})
    return {"sent": True, "email_id": email_id}


async def run_due_watch_alerts() -> int:
    """Send email for any triggered price-watch whose cooldown has elapsed."""
    if not os.environ.get("EMERGENT_EMAIL_KEY"):
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WATCH_COOLDOWN_HOURS)
    sent = 0
    cursor = db.gaming_watches.find({"notify_email": True}, {"_id": 0})
    async for watch in cursor:
        last = watch.get("last_notified_at")
        if last:
            try:
                if datetime.fromisoformat(last.replace("Z", "+00:00")) > cutoff:
                    continue
            except ValueError:
                pass
        try:
            result = await send_watch_alert_now(watch["id"], watch["user_id"], force=False)
            if result.get("sent"):
                sent += 1
        except Exception:
            logger.exception("watch alert failed for %s", watch["id"])
    return sent
