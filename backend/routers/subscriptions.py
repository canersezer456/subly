import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from lib.auth import get_current_user
from lib.db import db
from models.subscription import Deal, MockScanResponse, Subscription, SubscriptionCreate, SubscriptionUpdate

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _subscription(doc: dict) -> Subscription:
    return Subscription(**doc)


@router.get("", response_model=list[Subscription])
async def list_subscriptions(user: dict = Depends(get_current_user)):
    docs = await db.subscriptions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("renewal_date", 1).to_list(100)
    return [_subscription(doc) for doc in docs]


@router.post("", response_model=Subscription)
async def create_subscription(input: SubscriptionCreate, user: dict = Depends(get_current_user)):
    doc = input.model_dump()
    doc.update({"id": str(uuid.uuid4()), "user_id": user["user_id"], "status": "active", "created_at": datetime.now(timezone.utc).isoformat()})
    await db.subscriptions.insert_one(doc)
    return _subscription(doc)


@router.patch("/{subscription_id}", response_model=Subscription)
async def update_subscription(subscription_id: str, input: SubscriptionUpdate, user: dict = Depends(get_current_user)):
    changes = input.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
    result = await db.subscriptions.update_one({"id": subscription_id, "user_id": user["user_id"]}, {"$set": changes})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı")
    doc = await db.subscriptions.find_one({"id": subscription_id, "user_id": user["user_id"]}, {"_id": 0})
    return _subscription(doc)


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(subscription_id: str, user: dict = Depends(get_current_user)):
    result = await db.subscriptions.delete_one({"id": subscription_id, "user_id": user["user_id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı")


@router.post("/mock-scan", response_model=MockScanResponse)
async def mock_scan(user: dict = Depends(get_current_user)):
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
