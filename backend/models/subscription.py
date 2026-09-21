from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=40)
    price: float = Field(gt=0, le=100000)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    renewal_date: str = Field(min_length=10, max_length=10)
    payment_method: str = Field(default="Kart •••• 4821", max_length=60)
    cancellation_url: str = Field(default="https://www.google.com", max_length=500)
    source: str = Field(default="manual", max_length=20)
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    usage: str = Field(default="active", pattern="^(active|rarely|unused)$")


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    category: str | None = Field(default=None, min_length=2, max_length=40)
    price: float | None = Field(default=None, gt=0, le=100000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    renewal_date: str | None = Field(default=None, min_length=10, max_length=10)
    payment_method: str | None = Field(default=None, max_length=60)
    cancellation_url: str | None = Field(default=None, max_length=500)
    source: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=30)
    billing_cycle: str | None = Field(default=None, pattern="^(monthly|yearly)$")
    usage: str | None = Field(default=None, pattern="^(active|rarely|unused)$")


class Subscription(SubscriptionCreate):
    id: str
    status: str = "active"
    created_at: str


class MockScanResponse(BaseModel):
    scan_id: str
    mocked: bool = True
    detected: list[SubscriptionCreate]


class Deal(BaseModel):
    id: str
    title: str
    provider: str
    category: str
    description: str
    current_price: float
    discounted_price: float
    savings: float
    currency: str = "TRY"
    url: str
    badge: str
    discount_percent: int
    featured: bool = False
    partner_status: str = "example"
