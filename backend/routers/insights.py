from fastapi import APIRouter, Depends, HTTPException, Query

from lib import finance
from lib.auth import get_current_user
from lib.db import db
from lib.gaming_catalog import apply_overrides, catalog
from models.finance import Alert, CalendarResponse, DashboardSummary, SavingsReport

router = APIRouter(tags=["insights"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(user: dict = Depends(get_current_user)):
    data = await finance.load_user_data(user["user_id"])
    return finance.summary(data, finance.today())


@router.get("/calendar", response_model=CalendarResponse)
async def calendar_view(month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"), user: dict = Depends(get_current_user)):
    key = month or finance.month_key(finance.today())
    try:
        finance.month_bounds(key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Geçersiz ay") from exc
    data = await finance.load_user_data(user["user_id"])
    return finance.calendar(data, key)


@router.get("/savings", response_model=SavingsReport)
async def savings(user: dict = Depends(get_current_user)):
    data = await finance.load_user_data(user["user_id"])
    key = finance.month_key(finance.today())
    insights = finance.savings_insights(data, key)
    order = {"red": 0, "yellow": 1, "green": 2}
    insights.sort(key=lambda i: (order.get(i["level"], 9), -i["amount"]))
    return {"total": round(sum(i["amount"] for i in insights), 2), "insights": insights, "unused_subscriptions": sum(1 for s in finance.active_subs(data["subscriptions"]) if s.get("usage") == "unused")}


async def _gaming_watch_alerts(user_id: str) -> list[dict]:
    docs = await db.gaming_watches.find({"user_id": user_id, "notify_in_app": True}, {"_id": 0}).to_list(200)
    if not docs:
        return []
    overrides = await db.gaming_price_overrides.find({"user_id": user_id}, {"_id": 0}).to_list(2000)
    cat = apply_overrides(catalog(), overrides)
    alerts: list[dict] = []
    for doc in docs:
        offers = cat["offers_by_product"].get(doc["product_id"], [])
        if not offers:
            continue
        best = offers[0]
        if best["price_try"] <= doc["target_price_try"]:
            product = cat["products_by_id"].get(doc["product_id"])
            title = product["name"] if product else "Ürün"
            alerts.append({
                "id": f"gaming-watch-{doc['id']}",
                "level": "success",
                "message": f"🎮 {title} takip fiyatın altında: {best['seller_name']} · {best['price_try']:.2f} ₺",
                "path": f"/gaming/products/{doc['product_id']}",
            })
    return alerts


@router.get("/alerts", response_model=list[Alert])
async def alerts(user: dict = Depends(get_current_user)):
    data = await finance.load_user_data(user["user_id"])
    ref = finance.today()
    base = finance.alerts(data, ref, finance.month_key(ref))
    gaming = await _gaming_watch_alerts(user["user_id"])
    return base + gaming
