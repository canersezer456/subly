"""Gaming module.

Endpoints:
  Public:
    GET  /gaming/home                     — sections + games + sellers
    GET  /gaming/games                    — list games
    GET  /gaming/games/{slug}             — game detail (with products)
    GET  /gaming/products/{product_id}    — product detail (with offers)
    GET  /gaming/search?q=...             — search games + products
    GET  /gaming/sellers                  — seller directory

  Purchases + expenses linkage:
    POST /gaming/purchases                — record (creates linked expense)
    GET  /gaming/purchases                — list with optional ?month=
    GET  /gaming/summary?month=           — monthly total + top games
    DELETE /gaming/purchases/{id}         — cascade-delete linked expense

  Admin catalog editor (per user overrides):
    GET  /gaming/admin/catalog            — flat list of every offer with base + current
    PUT  /gaming/admin/catalog/{offer_id} — set/update override for one offer
    DELETE /gaming/admin/catalog/{offer_id} — clear override for one offer
    POST /gaming/admin/catalog/import     — bulk JSON import
    POST /gaming/admin/catalog/reset      — remove all user overrides

  Price watch list ("Fırsat Uyarıları"):
    GET    /gaming/watches                — list with live status
    POST   /gaming/watches                — create
    PATCH  /gaming/watches/{watch_id}     — update target/notification
    DELETE /gaming/watches/{watch_id}     — delete

  Affiliate earnings:
    GET  /gaming/earnings?month=          — monthly commission summary
    GET  /gaming/earnings/all             — all-time totals

  Gaming budget (thin wrapper over budgets collection):
    GET  /gaming/budget?month=            — current status
    PUT  /gaming/budget                   — set/update the Gaming budget
    DELETE /gaming/budget                 — clear
"""

import csv
import itertools
import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File

from lib import finance
from lib.auth import get_current_user
from lib.db import db
from lib.gaming_catalog import apply_affiliate, apply_overrides, catalog, commission_rate
from models.gaming import (
    GamingBudgetSet,
    GamingBudgetStatus,
    GamingBulkImport,
    GamingCatalogAdminRow,
    GamingCatalogHistoryEntry,
    GamingDeal,
    GamingEarningsBySeller,
    GamingEarningsSummary,
    GamingEarningsTrend,
    GamingEarningsTrendPoint,
    GamingGame,
    GamingGameDetail,
    GamingHome,
    GamingImportResult,
    GamingOffer,
    GamingOfferOverrideInput,
    GamingProduct,
    GamingProductDetail,
    GamingPurchase,
    GamingPurchaseCreate,
    GamingPurchaseResponse,
    GamingSeller,
    GamingWatch,
    GamingWatchCreate,
    GamingWatchUpdate,
)

router = APIRouter(prefix="/gaming", tags=["gaming"])

GAMING_CATEGORY = "Gaming"
CATALOG_NOTE = (
    "Fiyatlar elle güncellenen küratörlü katalogdur; Katalog Düzenle ekranından bu ürünlere ait fiyatları "
    "kendi güncel değerlerinle değiştirebilirsin. Resmi affiliate/API entegrasyonu bağlandığında bu şema "
    "aynen gerçek zamanlı beslenecek."
)


async def _user_overrides(user_id: str) -> list[dict]:
    return await db.gaming_price_overrides.find({"user_id": user_id}, {"_id": 0}).to_list(2000)


async def _user_catalog(user_id: str) -> dict:
    overrides = await _user_overrides(user_id)
    return apply_overrides(catalog(), overrides)


def _game_public(game: dict) -> GamingGame:
    return GamingGame(
        slug=game["slug"],
        name=game["name"],
        currency=game["currency"],
        category=game["category"],
        accent_color=game["accent_color"],
        icon_url=game["icon_url"],
        tagline=game["tagline"],
        popular=game["popular"],
        product_count=game["product_count"],
        best_price_try=game["best_price_try"],
    )


def _product_public(product: dict) -> GamingProduct:
    return GamingProduct(**{k: v for k, v in product.items() if not k.startswith("_")})


def _offer_public(offer: dict, override_ids: set[str] | None = None) -> GamingOffer:
    rate = commission_rate(offer["seller_id"])
    return GamingOffer(
        id=offer["id"],
        product_id=offer["product_id"],
        seller_id=offer["seller_id"],
        seller_name=offer["seller_name"],
        seller_reliability=offer["seller_reliability"],
        seller_domain=offer["seller_domain"],
        price_try=offer["price_try"],
        original_price_try=offer.get("original_price_try"),
        delivery=offer["delivery"],
        stock=offer.get("stock", "in_stock"),
        verified=offer.get("verified", True),
        campaign=offer.get("campaign"),
        url=apply_affiliate(offer["url"], offer["seller_id"]),
        updated_at=offer["updated_at"],
        has_override=bool(override_ids and offer["id"] in override_ids),
        estimated_commission_try=round(offer["price_try"] * rate, 2),
    )


def _seller_public(seller: dict) -> GamingSeller:
    return GamingSeller(**seller)


def _deal_from_offer(offer: dict, product: dict, game: dict) -> GamingDeal:
    original = offer.get("original_price_try") or offer["price_try"]
    discount = max(0, round((1 - offer["price_try"] / original) * 100)) if original and original > offer["price_try"] else 0
    return GamingDeal(
        offer_id=offer["id"],
        product_id=product["id"],
        product_name=product["name"],
        game_slug=game["slug"],
        game_name=game["name"],
        game_currency=game["currency"],
        accent_color=game["accent_color"],
        price_try=offer["price_try"],
        original_price_try=offer.get("original_price_try"),
        discount_percent=discount,
        seller_name=offer["seller_name"],
        seller_reliability=offer["seller_reliability"],
        delivery=offer["delivery"],
        campaign=offer.get("campaign"),
        url=apply_affiliate(offer["url"], offer["seller_id"]),
    )


def _lookup_offer(cat: dict, offer_id: str) -> tuple[dict, dict, dict]:
    for product_id, offers in cat["offers_by_product"].items():
        for offer in offers:
            if offer["id"] == offer_id:
                product = cat["products_by_id"][product_id]
                game = next((g for g in cat["games"] if g["slug"] == product["game_slug"]), None)
                if not game:
                    raise HTTPException(status_code=500, detail="Oyun bulunamadı")
                return offer, product, game
    raise HTTPException(status_code=404, detail="Teklif bulunamadı")


def _game_of(product_id: str, cat: dict) -> dict:
    product = cat["products_by_id"].get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    game = next((g for g in cat["games"] if g["slug"] == product["game_slug"]), None)
    if not game:
        raise HTTPException(status_code=500, detail="Oyun bulunamadı")
    return game


# ---- Read paths ---------------------------------------------------------


@router.get("/home", response_model=GamingHome)
async def gaming_home(user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    games = cat["games"]

    all_offer_ctx: list[tuple[dict, dict, dict]] = []
    for game in games:
        for product_id in game["_product_ids"]:
            product = cat["products_by_id"][product_id]
            for offer in cat["offers_by_product"][product_id]:
                all_offer_ctx.append((offer, product, game))

    seen_products: set[str] = set()
    cheapest: list[GamingDeal] = []
    for offer, product, game in sorted(all_offer_ctx, key=lambda t: t[0]["price_try"]):
        if offer["seller_reliability"] not in ("verified", "trusted"):
            continue
        if product["id"] in seen_products:
            continue
        seen_products.add(product["id"])
        cheapest.append(_deal_from_offer(offer, product, game))
        if len(cheapest) >= 8:
            break

    campaigns_seen: set[str] = set()
    campaigns: list[GamingDeal] = []
    for offer, product, game in all_offer_ctx:
        if not (offer.get("campaign") or offer.get("original_price_try")):
            continue
        if product["id"] in campaigns_seen:
            continue
        campaigns_seen.add(product["id"])
        campaigns.append(_deal_from_offer(offer, product, game))
    campaigns.sort(key=lambda d: (d.discount_percent, -d.price_try), reverse=True)
    campaigns = campaigns[:8]

    instant_seen: set[str] = set()
    instant: list[GamingDeal] = []
    for offer, product, game in sorted(all_offer_ctx, key=lambda t: t[0]["price_try"]):
        if offer["delivery"] != "Anında":
            continue
        if product["id"] in instant_seen:
            continue
        instant_seen.add(product["id"])
        instant.append(_deal_from_offer(offer, product, game))
        if len(instant) >= 8:
            break

    today_deals: list[GamingDeal] = []
    today_seen: set[str] = set()
    for deal in campaigns:
        if deal.product_id in today_seen:
            continue
        today_seen.add(deal.product_id)
        today_deals.append(deal)
        if len(today_deals) >= 6:
            break
    if len(today_deals) < 6:
        for deal in cheapest:
            if deal.product_id in today_seen:
                continue
            today_seen.add(deal.product_id)
            today_deals.append(deal)
            if len(today_deals) >= 6:
                break

    return GamingHome(
        updated_at=cat["updated_at"],
        catalog_note=CATALOG_NOTE,
        popular_games=[_game_public(g) for g in games if g["popular"]],
        all_games=[_game_public(g) for g in games],
        cheapest_offers=cheapest,
        campaigns=campaigns,
        instant_delivery=instant,
        today_deals=today_deals,
        sellers=[_seller_public(s) for s in cat["sellers"]],
    )


@router.get("/games", response_model=list[GamingGame])
async def list_games(user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    return [_game_public(g) for g in cat["games"]]


@router.get("/games/{slug}", response_model=GamingGameDetail)
async def game_detail(slug: str, user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    game = next((g for g in cat["games"] if g["slug"] == slug), None)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı")
    products = [_product_public(cat["products_by_id"][pid]) for pid in game["_product_ids"]]
    return GamingGameDetail(**_game_public(game).model_dump(), products=products)


@router.get("/products/{product_id}", response_model=GamingProductDetail)
async def product_detail(product_id: str, user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    product = cat["products_by_id"].get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    overrides = await _user_overrides(user["user_id"])
    override_ids = {o["offer_id"] for o in overrides}
    offers = [_offer_public(o, override_ids) for o in cat["offers_by_product"].get(product_id, [])]
    reliability_rank = {"verified": 0, "trusted": 1, "caution": 2}
    offers.sort(key=lambda o: (reliability_rank.get(o.seller_reliability, 3), o.price_try))
    return GamingProductDetail(**_product_public(product).model_dump(), offers=offers)


@router.get("/search")
async def search(q: str = Query(min_length=1, max_length=80), user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    query = q.strip().lower()
    games_hit: list[GamingGame] = []
    products_hit: list[GamingProduct] = []
    for game in cat["games"]:
        if query in game["name"].lower() or query in game["slug"].lower() or query in game["currency"].lower():
            games_hit.append(_game_public(game))
    for product in cat["products_by_id"].values():
        if query in product["name"].lower() or query in product["game_name"].lower() or query in product["game_currency"].lower():
            products_hit.append(_product_public(product))
    return {"games": games_hit, "products": products_hit[:20]}


@router.get("/sellers", response_model=list[GamingSeller])
async def sellers(user: dict = Depends(get_current_user)):  # noqa: ARG001
    return [_seller_public(s) for s in catalog()["sellers"]]


# ---- Purchases ----------------------------------------------------------


@router.post("/purchases", response_model=GamingPurchaseResponse, status_code=201)
async def record_purchase(input: GamingPurchaseCreate, user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    offer, product, game = _lookup_offer(cat, input.offer_id)
    if offer["product_id"] != input.product_id or offer["seller_id"] != input.seller_id:
        raise HTTPException(status_code=400, detail="Teklif ile ürün/satıcı uyuşmuyor")

    date = input.date or datetime.now(timezone.utc).date().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    rate = commission_rate(offer["seller_id"])
    commission = round(float(input.amount_try) * rate, 2)

    expense_id = str(uuid.uuid4())
    purchase_id = str(uuid.uuid4())
    title = f"{game['name']} · {product['name']}"

    expense_doc = {
        "id": expense_id,
        "user_id": user["user_id"],
        "title": title,
        "amount": float(input.amount_try),
        "category": GAMING_CATEGORY,
        "date": date,
        "payment_method": input.payment_method,
        "note": (input.note or f"{offer['seller_name']} üzerinden Gaming satın alması").strip(),
        "created_at": now_iso,
        "source": "gaming",
        "gaming_purchase_id": purchase_id,
    }
    await db.expenses.insert_one(expense_doc)

    purchase_doc = {
        "id": purchase_id,
        "user_id": user["user_id"],
        "offer_id": input.offer_id,
        "product_id": product["id"],
        "product_name": product["name"],
        "game_slug": game["slug"],
        "game_name": game["name"],
        "seller_id": offer["seller_id"],
        "seller_name": offer["seller_name"],
        "amount_try": float(input.amount_try),
        "payment_method": input.payment_method,
        "date": date,
        "note": input.note or "",
        "expense_id": expense_id,
        "created_at": now_iso,
        "estimated_commission_try": commission,
        "commission_rate": rate,
    }
    await db.gaming_purchases.insert_one(purchase_doc)

    month = date[:7]
    monthly = await db.gaming_purchases.find({"user_id": user["user_id"], "date": {"$regex": f"^{month}"}}, {"_id": 0}).to_list(1000)
    monthly_total = sum(item["amount_try"] for item in monthly)

    return GamingPurchaseResponse(
        purchase=GamingPurchase(**purchase_doc),
        monthly_total=monthly_total,
        monthly_count=len(monthly),
    )


@router.get("/purchases", response_model=list[GamingPurchase])
async def list_purchases(month: str | None = Query(default=None, max_length=7), user: dict = Depends(get_current_user)):
    query: dict = {"user_id": user["user_id"]}
    if month:
        query["date"] = {"$regex": f"^{month}"}
    docs = await db.gaming_purchases.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return [GamingPurchase(**doc) for doc in docs]


@router.get("/summary")
async def gaming_summary(month: str | None = Query(default=None, max_length=7), user: dict = Depends(get_current_user)):
    month_key = month or datetime.now(timezone.utc).date().isoformat()[:7]
    docs = await db.gaming_purchases.find({"user_id": user["user_id"], "date": {"$regex": f"^{month_key}"}}, {"_id": 0}).to_list(1000)
    monthly_total = sum(item["amount_try"] for item in docs)
    by_game: dict[str, float] = {}
    for item in docs:
        by_game[item["game_name"]] = by_game.get(item["game_name"], 0.0) + item["amount_try"]
    top = sorted(({"game": name, "amount": amount} for name, amount in by_game.items()), key=lambda x: x["amount"], reverse=True)[:5]
    return {"month": month_key, "total": monthly_total, "count": len(docs), "top_games": top}


@router.delete("/purchases/{purchase_id}", status_code=204)
async def delete_purchase(purchase_id: str, user: dict = Depends(get_current_user)):
    purchase = await db.gaming_purchases.find_one({"id": purchase_id, "user_id": user["user_id"]}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Satın alma bulunamadı")
    await db.gaming_purchases.delete_one({"id": purchase_id, "user_id": user["user_id"]})
    if purchase.get("expense_id"):
        await db.expenses.delete_one({"id": purchase["expense_id"], "user_id": user["user_id"]})


# ---- Admin catalog editor ----------------------------------------------


def _admin_row(base_offer: dict, override: dict | None, base_product: dict, base_game: dict) -> GamingCatalogAdminRow:
    return GamingCatalogAdminRow(
        offer_id=base_offer["id"],
        product_id=base_product["id"],
        game_slug=base_game["slug"],
        game_name=base_game["name"],
        product_name=base_product["name"],
        seller_id=base_offer["seller_id"],
        seller_name=base_offer["seller_name"],
        seller_reliability=base_offer["seller_reliability"],
        base_price_try=base_offer["price_try"],
        current_price_try=float(override["price_try"]) if override and override.get("price_try") is not None else base_offer["price_try"],
        base_original_price_try=base_offer.get("original_price_try"),
        current_original_price_try=float(override["original_price_try"]) if override and override.get("original_price_try") is not None else base_offer.get("original_price_try"),
        base_delivery=base_offer["delivery"],
        current_delivery=override["delivery"] if override and override.get("delivery") else base_offer["delivery"],
        base_campaign=base_offer.get("campaign"),
        current_campaign=override.get("campaign") if override and "campaign" in override else base_offer.get("campaign"),
        base_url=base_offer["url"],
        current_url=override["url"] if override and override.get("url") else base_offer["url"],
        has_override=bool(override),
        updated_at=override.get("updated_at") if override else None,
    )


# changed_at has coarse clock resolution (Windows ~15ms), so three fast writes can
# share one timestamp; a monotonic tiebreaker keeps history ordering deterministic.
_HISTORY_SEQ = itertools.count(1)

_OVERRIDE_FIELDS = ("price_try", "original_price_try", "delivery", "campaign", "url")


def _snapshot(doc: dict | None) -> dict | None:
    if not doc:
        return None
    snap = {k: doc[k] for k in _OVERRIDE_FIELDS if k in doc}
    return snap or None


async def _record_history(user_id: str, offer_id: str, before: dict | None, after: dict | None, action: str) -> None:
    base = catalog()
    try:
        base_offer, base_product, base_game = _lookup_offer(base, offer_id)
    except HTTPException:
        return
    await db.gaming_price_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "offer_id": offer_id,
        "product_id": base_product["id"],
        "game_slug": base_game["slug"],
        "game_name": base_game["name"],
        "product_name": base_product["name"],
        "seller_id": base_offer["seller_id"],
        "seller_name": base_offer["seller_name"],
        "action": action,
        "before": _snapshot(before),
        "after": _snapshot(after),
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "seq": next(_HISTORY_SEQ),
    })


@router.get("/admin/catalog", response_model=list[GamingCatalogAdminRow])
async def admin_catalog_list(user: dict = Depends(get_current_user)):
    base = catalog()
    overrides = await _user_overrides(user["user_id"])
    ov_by_id = {o["offer_id"]: o for o in overrides}
    rows: list[GamingCatalogAdminRow] = []
    for game in base["games"]:
        for pid in game["_product_ids"]:
            product = base["products_by_id"][pid]
            for offer in base["offers_by_product"][pid]:
                rows.append(_admin_row(offer, ov_by_id.get(offer["id"]), product, game))
    return rows


@router.put("/admin/catalog/{offer_id}", response_model=GamingCatalogAdminRow)
async def admin_catalog_set(offer_id: str, input: GamingOfferOverrideInput, user: dict = Depends(get_current_user)):
    base = catalog()
    base_offer, base_product, base_game = _lookup_offer(base, offer_id)
    payload = input.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
    before = await db.gaming_price_overrides.find_one({"offer_id": offer_id, "user_id": user["user_id"]}, {"_id": 0})
    action = "modify" if before else "override"
    payload.update({
        "offer_id": offer_id,
        "user_id": user["user_id"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.gaming_price_overrides.update_one(
        {"offer_id": offer_id, "user_id": user["user_id"]},
        {"$set": payload},
        upsert=True,
    )
    after = await db.gaming_price_overrides.find_one({"offer_id": offer_id, "user_id": user["user_id"]}, {"_id": 0})
    await _record_history(user["user_id"], offer_id, before, after, action)
    return _admin_row(base_offer, after, base_product, base_game)


@router.delete("/admin/catalog/{offer_id}", status_code=204)
async def admin_catalog_clear(offer_id: str, user: dict = Depends(get_current_user)):
    before = await db.gaming_price_overrides.find_one({"offer_id": offer_id, "user_id": user["user_id"]}, {"_id": 0})
    result = await db.gaming_price_overrides.delete_one({"offer_id": offer_id, "user_id": user["user_id"]})
    if before and result.deleted_count:
        await _record_history(user["user_id"], offer_id, before, None, "delete")


@router.post("/admin/catalog/import", response_model=GamingImportResult)
async def admin_catalog_import(payload: GamingBulkImport, user: dict = Depends(get_current_user)):
    base = catalog()
    known_ids = {o["id"] for o in base["all_offers"]}
    applied = 0
    skipped = 0
    errors: list[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for row in payload.overrides:
        if row.offer_id not in known_ids:
            errors.append(f"Bilinmeyen teklif: {row.offer_id}")
            skipped += 1
            continue
        data = row.model_dump(exclude_none=True)
        data.pop("offer_id", None)
        if not data:
            skipped += 1
            continue
        before = await db.gaming_price_overrides.find_one({"offer_id": row.offer_id, "user_id": user["user_id"]}, {"_id": 0})
        data.update({"offer_id": row.offer_id, "user_id": user["user_id"], "updated_at": now_iso})
        await db.gaming_price_overrides.update_one(
            {"offer_id": row.offer_id, "user_id": user["user_id"]},
            {"$set": data},
            upsert=True,
        )
        after = await db.gaming_price_overrides.find_one({"offer_id": row.offer_id, "user_id": user["user_id"]}, {"_id": 0})
        await _record_history(user["user_id"], row.offer_id, before, after, "bulk_import")
        applied += 1
    return GamingImportResult(applied=applied, skipped=skipped, errors=errors[:20])


@router.post("/admin/catalog/import/csv", response_model=GamingImportResult)
async def admin_catalog_import_csv(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Yalnızca .csv dosyaları desteklenir")
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    from models.gaming import GamingBulkImportRow

    for line in reader:
        offer_id = (line.get("offer_id") or "").strip()
        if not offer_id:
            continue
        price = line.get("price_try") or line.get("price")
        original = line.get("original_price_try") or line.get("original_price")
        delivery = (line.get("delivery") or "").strip() or None
        campaign = (line.get("campaign") or "").strip() or None
        url = (line.get("url") or "").strip() or None
        try:
            rows.append(GamingBulkImportRow(
                offer_id=offer_id,
                price_try=float(price) if price not in (None, "", "-") else None,
                original_price_try=float(original) if original not in (None, "", "-") else None,
                delivery=delivery,
                campaign=campaign,
                url=url,
            ))
        except (ValueError, TypeError):
            continue
    return await admin_catalog_import(GamingBulkImport(overrides=rows), user)


@router.post("/admin/catalog/reset", status_code=204)
async def admin_catalog_reset(user: dict = Depends(get_current_user)):
    existing = await db.gaming_price_overrides.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(2000)
    if not existing:
        return
    await db.gaming_price_overrides.delete_many({"user_id": user["user_id"]})
    for ov in existing:
        await _record_history(user["user_id"], ov["offer_id"], ov, None, "reset")


@router.get("/admin/catalog/history", response_model=list[GamingCatalogHistoryEntry])
async def admin_catalog_history(offer_id: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200), user: dict = Depends(get_current_user)):
    query: dict = {"user_id": user["user_id"]}
    if offer_id:
        query["offer_id"] = offer_id
    docs = await db.gaming_price_history.find(query, {"_id": 0}).sort([("changed_at", -1), ("seq", -1)]).to_list(limit)
    return [GamingCatalogHistoryEntry(**doc) for doc in docs]


@router.post("/admin/catalog/history/{history_id}/revert", response_model=GamingCatalogAdminRow)
async def admin_catalog_revert(history_id: str, user: dict = Depends(get_current_user)):
    entry = await db.gaming_price_history.find_one({"id": history_id, "user_id": user["user_id"]}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Geçmiş kaydı bulunamadı")
    offer_id = entry["offer_id"]
    base = catalog()
    base_offer, base_product, base_game = _lookup_offer(base, offer_id)
    current = await db.gaming_price_overrides.find_one({"offer_id": offer_id, "user_id": user["user_id"]}, {"_id": 0})
    before_snap = entry.get("before")
    now_iso = datetime.now(timezone.utc).isoformat()
    if before_snap is None:
        # Original state had no override → delete current override to return to base
        if current:
            await db.gaming_price_overrides.delete_one({"offer_id": offer_id, "user_id": user["user_id"]})
            await _record_history(user["user_id"], offer_id, current, None, "revert")
        result_doc = None
    else:
        payload = {**before_snap, "offer_id": offer_id, "user_id": user["user_id"], "updated_at": now_iso}
        await db.gaming_price_overrides.update_one(
            {"offer_id": offer_id, "user_id": user["user_id"]},
            {"$set": payload},
            upsert=True,
        )
        result_doc = await db.gaming_price_overrides.find_one({"offer_id": offer_id, "user_id": user["user_id"]}, {"_id": 0})
        await _record_history(user["user_id"], offer_id, current, result_doc, "revert")
    return _admin_row(base_offer, result_doc, base_product, base_game)


# ---- Price watch list ---------------------------------------------------


def _watch_from_doc(doc: dict, cat: dict) -> GamingWatch:
    product = cat["products_by_id"].get(doc["product_id"])
    game = _game_of(doc["product_id"], cat) if product else None
    offers = cat["offers_by_product"].get(doc["product_id"], [])
    best_offer = offers[0] if offers else None
    current_price = best_offer["price_try"] if best_offer else 0.0
    return GamingWatch(
        id=doc["id"],
        user_id=doc["user_id"],
        product_id=doc["product_id"],
        product_name=product["name"] if product else "Kaldırılmış ürün",
        game_slug=game["slug"] if game else "",
        game_name=game["name"] if game else "",
        game_currency=game["currency"] if game else "",
        accent_color=game["accent_color"] if game else "#888888",
        target_price_try=doc["target_price_try"],
        current_price_try=current_price,
        best_seller_name=best_offer["seller_name"] if best_offer else None,
        best_offer_id=best_offer["id"] if best_offer else None,
        best_offer_url=apply_affiliate(best_offer["url"], best_offer["seller_id"]) if best_offer else None,
        triggered=bool(best_offer and current_price <= doc["target_price_try"]),
        notify_email=doc.get("notify_email", True),
        notify_in_app=doc.get("notify_in_app", True),
        note=doc.get("note", ""),
        last_notified_at=doc.get("last_notified_at"),
        created_at=doc["created_at"],
    )


@router.get("/watches", response_model=list[GamingWatch])
async def list_watches(user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    docs = await db.gaming_watches.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [_watch_from_doc(doc, cat) for doc in docs]


@router.post("/watches", response_model=GamingWatch, status_code=201)
async def create_watch(input: GamingWatchCreate, user: dict = Depends(get_current_user)):
    cat = await _user_catalog(user["user_id"])
    if input.product_id not in cat["products_by_id"]:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "product_id": input.product_id,
        "target_price_try": float(input.target_price_try),
        "notify_email": input.notify_email,
        "notify_in_app": input.notify_in_app,
        "note": input.note,
        "last_notified_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.gaming_watches.insert_one(doc)
    return _watch_from_doc(doc, cat)


@router.patch("/watches/{watch_id}", response_model=GamingWatch)
async def update_watch(watch_id: str, input: GamingWatchUpdate, user: dict = Depends(get_current_user)):
    changes = input.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
    if "target_price_try" in changes:
        changes["target_price_try"] = float(changes["target_price_try"])
    result = await db.gaming_watches.update_one({"id": watch_id, "user_id": user["user_id"]}, {"$set": changes})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Uyarı bulunamadı")
    doc = await db.gaming_watches.find_one({"id": watch_id, "user_id": user["user_id"]}, {"_id": 0})
    cat = await _user_catalog(user["user_id"])
    return _watch_from_doc(doc, cat)


@router.delete("/watches/{watch_id}", status_code=204)
async def delete_watch(watch_id: str, user: dict = Depends(get_current_user)):
    result = await db.gaming_watches.delete_one({"id": watch_id, "user_id": user["user_id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Uyarı bulunamadı")


# ---- Affiliate earnings -------------------------------------------------


@router.get("/earnings", response_model=GamingEarningsSummary)
async def earnings_month(month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"), user: dict = Depends(get_current_user)):
    month_key = month or datetime.now(timezone.utc).date().isoformat()[:7]
    docs = await db.gaming_purchases.find({"user_id": user["user_id"], "date": {"$regex": f"^{month_key}"}}, {"_id": 0}).to_list(2000)
    by_seller: dict[str, dict] = {}
    for item in docs:
        seller_id = item.get("seller_id", "unknown")
        seller_name = item.get("seller_name", "Bilinmeyen")
        commission = float(item.get("estimated_commission_try") or 0.0) or round(float(item["amount_try"]) * commission_rate(seller_id), 2)
        row = by_seller.setdefault(seller_id, {"seller_id": seller_id, "seller_name": seller_name, "total_spent": 0.0, "commission": 0.0, "count": 0})
        row["total_spent"] += float(item["amount_try"])
        row["commission"] += commission
        row["count"] += 1
    return GamingEarningsSummary(
        month=month_key,
        month_label=finance.month_label(month_key),
        total_spent=round(sum(r["total_spent"] for r in by_seller.values()), 2),
        total_commission=round(sum(r["commission"] for r in by_seller.values()), 2),
        count=len(docs),
        by_seller=sorted((GamingEarningsBySeller(**r) for r in by_seller.values()), key=lambda x: x.commission, reverse=True),
    )


@router.get("/earnings/all")
async def earnings_all_time(user: dict = Depends(get_current_user)):
    docs = await db.gaming_purchases.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(5000)
    total_spent = sum(float(item["amount_try"]) for item in docs)
    total_commission = 0.0
    for item in docs:
        c = float(item.get("estimated_commission_try") or 0.0)
        if c:
            total_commission += c
        else:
            total_commission += round(float(item["amount_try"]) * commission_rate(item.get("seller_id", "")), 2)
    return {"total_spent": round(total_spent, 2), "total_commission": round(total_commission, 2), "count": len(docs)}


@router.get("/earnings/trend", response_model=GamingEarningsTrend)
async def earnings_trend(months: int = Query(default=6, ge=1, le=24), user: dict = Depends(get_current_user)):
    today = finance.today()
    current_key = finance.month_key(today)
    keys = [finance.shift_month(current_key, -i) for i in range(months - 1, -1, -1)]
    range_from = f"{keys[0]}-01"
    range_to = f"{keys[-1]}-31"
    docs = await db.gaming_purchases.find({"user_id": user["user_id"], "date": {"$gte": range_from, "$lte": range_to}}, {"_id": 0}).to_list(5000)

    per_month: dict[str, dict] = {k: {"total_spent": 0.0, "total_commission": 0.0, "count": 0} for k in keys}
    by_seller: dict[str, dict] = {}
    for item in docs:
        mk = item["date"][:7]
        if mk not in per_month:
            continue
        commission = float(item.get("estimated_commission_try") or 0.0) or round(float(item["amount_try"]) * commission_rate(item.get("seller_id", "")), 2)
        per_month[mk]["total_spent"] += float(item["amount_try"])
        per_month[mk]["total_commission"] += commission
        per_month[mk]["count"] += 1
        row = by_seller.setdefault(item.get("seller_id", "unknown"), {"seller_id": item.get("seller_id", "unknown"), "seller_name": item.get("seller_name", "Bilinmeyen"), "total_spent": 0.0, "commission": 0.0, "count": 0})
        row["total_spent"] += float(item["amount_try"])
        row["commission"] += commission
        row["count"] += 1

    points = [GamingEarningsTrendPoint(month=k, month_label=finance.month_label(k), total_spent=round(v["total_spent"], 2), total_commission=round(v["total_commission"], 2), count=v["count"]) for k, v in per_month.items()]
    return GamingEarningsTrend(
        months=months,
        range_from=keys[0],
        range_to=keys[-1],
        total_spent=round(sum(p.total_spent for p in points), 2),
        total_commission=round(sum(p.total_commission for p in points), 2),
        count=sum(p.count for p in points),
        points=points,
        by_seller=sorted((GamingEarningsBySeller(**r) for r in by_seller.values()), key=lambda x: x.commission, reverse=True),
    )


# ---- Watch email trigger (manual + used by scheduler) -------------------


@router.post("/watches/{watch_id}/notify")
async def notify_watch(watch_id: str, user: dict = Depends(get_current_user)):
    """Send the price-alert email for a triggered watch now (respecting 24h cooldown)."""
    from lib.digest import send_watch_alert_now
    return await send_watch_alert_now(watch_id, user["user_id"], force=False)


# ---- Gaming budget ------------------------------------------------------


async def _spent_gaming_this_month(user_id: str, month_key: str) -> float:
    docs = await db.gaming_purchases.find({"user_id": user_id, "date": {"$regex": f"^{month_key}"}}, {"_id": 0}).to_list(2000)
    return round(sum(float(d["amount_try"]) for d in docs), 2)


async def _find_gaming_budget(user_id: str, month_key: str) -> dict | None:
    # Prefer month-specific, fall back to always-on (month == "")
    doc = await db.budgets.find_one({"user_id": user_id, "category": GAMING_CATEGORY, "month": month_key}, {"_id": 0})
    if doc:
        return doc
    return await db.budgets.find_one({"user_id": user_id, "category": GAMING_CATEGORY, "month": ""}, {"_id": 0})


@router.get("/budget", response_model=GamingBudgetStatus)
async def gaming_budget(month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"), user: dict = Depends(get_current_user)):
    month_key = month or datetime.now(timezone.utc).date().isoformat()[:7]
    budget_doc = await _find_gaming_budget(user["user_id"], month_key)
    spent = await _spent_gaming_this_month(user["user_id"], month_key)
    if not budget_doc:
        return GamingBudgetStatus(month=month_key, limit=None, spent=spent, percent=0.0, exceeded=False, warning=False)
    limit = float(budget_doc["limit"])
    percent = round((spent / limit) * 100, 1) if limit else 0.0
    return GamingBudgetStatus(
        month=month_key,
        limit=limit,
        spent=spent,
        percent=percent,
        exceeded=spent > limit,
        warning=percent >= 85 and spent <= limit,
    )


@router.put("/budget", response_model=GamingBudgetStatus)
async def set_gaming_budget(input: GamingBudgetSet, user: dict = Depends(get_current_user)):
    month = input.month or ""
    existing = await db.budgets.find_one({"user_id": user["user_id"], "category": GAMING_CATEGORY, "month": month}, {"_id": 0})
    now_iso = datetime.now(timezone.utc).isoformat()
    if existing:
        await db.budgets.update_one({"id": existing["id"], "user_id": user["user_id"]}, {"$set": {"limit": float(input.limit)}})
    else:
        await db.budgets.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "category": GAMING_CATEGORY,
            "limit": float(input.limit),
            "month": month,
            "created_at": now_iso,
        })
    return await gaming_budget(month=None, user=user)


@router.delete("/budget", status_code=204)
async def clear_gaming_budget(user: dict = Depends(get_current_user)):
    await db.budgets.delete_many({"user_id": user["user_id"], "category": GAMING_CATEGORY})
