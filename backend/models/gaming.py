from pydantic import BaseModel, Field


# ---- Public catalog ------------------------------------------------------


class GamingSeller(BaseModel):
    id: str
    name: str
    domain: str
    reliability: str  # verified | trusted | caution
    delivery: str  # Anında | 1-5 dk | 5-15 dk | Manuel
    return_policy: str
    payment_methods: list[str] = []
    note: str = ""


class GamingOffer(BaseModel):
    id: str
    product_id: str
    seller_id: str
    seller_name: str
    seller_reliability: str
    seller_domain: str
    price_try: float
    original_price_try: float | None = None
    delivery: str
    stock: str = "in_stock"  # in_stock | low | out
    verified: bool = True
    campaign: str | None = None
    url: str
    updated_at: str
    has_override: bool = False
    estimated_commission_try: float = 0.0


class GamingProduct(BaseModel):
    id: str
    game_slug: str
    game_name: str
    game_currency: str
    name: str
    amount: float
    unit: str
    description: str = ""
    tag: str | None = None  # popular | best_value | new
    icon: str = ""
    best_price_try: float | None = None
    offer_count: int = 0


class GamingGame(BaseModel):
    slug: str
    name: str
    currency: str
    category: str
    accent_color: str
    icon_url: str
    tagline: str
    popular: bool = False
    product_count: int = 0
    best_price_try: float | None = None


class GamingGameDetail(GamingGame):
    products: list[GamingProduct]


class GamingProductDetail(GamingProduct):
    offers: list[GamingOffer]


class GamingDeal(BaseModel):
    offer_id: str
    product_id: str
    product_name: str
    game_slug: str
    game_name: str
    game_currency: str
    accent_color: str
    price_try: float
    original_price_try: float | None
    discount_percent: int
    seller_name: str
    seller_reliability: str
    delivery: str
    campaign: str | None = None
    url: str


class GamingHome(BaseModel):
    updated_at: str
    catalog_note: str
    popular_games: list[GamingGame]
    all_games: list[GamingGame]
    cheapest_offers: list[GamingDeal]
    campaigns: list[GamingDeal]
    instant_delivery: list[GamingDeal]
    today_deals: list[GamingDeal]
    sellers: list[GamingSeller]


# ---- Purchases (write path) ---------------------------------------------


class GamingPurchaseCreate(BaseModel):
    offer_id: str
    product_id: str
    seller_id: str
    amount_try: float = Field(gt=0, le=1_000_000)
    payment_method: str = Field(default="Kart •••• 4821", max_length=60)
    note: str = Field(default="", max_length=300)
    date: str | None = Field(default=None, min_length=10, max_length=10)


class GamingPurchase(BaseModel):
    id: str
    user_id: str
    offer_id: str
    product_id: str
    product_name: str
    game_slug: str
    game_name: str
    seller_id: str
    seller_name: str
    amount_try: float
    payment_method: str
    date: str
    note: str
    expense_id: str
    created_at: str
    estimated_commission_try: float = 0.0
    commission_rate: float = 0.0


class GamingPurchaseResponse(BaseModel):
    purchase: GamingPurchase
    monthly_total: float
    monthly_count: int


# ---- Admin catalog editor ------------------------------------------------


class GamingOfferOverrideInput(BaseModel):
    price_try: float | None = Field(default=None, gt=0, le=1_000_000)
    original_price_try: float | None = Field(default=None, gt=0, le=1_000_000)
    delivery: str | None = Field(default=None, max_length=40)
    campaign: str | None = Field(default=None, max_length=80)
    url: str | None = Field(default=None, max_length=500)


class GamingCatalogAdminRow(BaseModel):
    offer_id: str
    product_id: str
    game_slug: str
    game_name: str
    product_name: str
    seller_id: str
    seller_name: str
    seller_reliability: str
    base_price_try: float
    current_price_try: float
    base_original_price_try: float | None
    current_original_price_try: float | None
    base_delivery: str
    current_delivery: str
    base_campaign: str | None
    current_campaign: str | None
    base_url: str
    current_url: str
    has_override: bool
    updated_at: str | None


class GamingBulkImportRow(BaseModel):
    offer_id: str
    price_try: float | None = None
    original_price_try: float | None = None
    delivery: str | None = None
    campaign: str | None = None
    url: str | None = None


class GamingBulkImport(BaseModel):
    overrides: list[GamingBulkImportRow]


class GamingImportResult(BaseModel):
    applied: int
    skipped: int
    errors: list[str] = []


# ---- Price watchlist -----------------------------------------------------


class GamingWatchCreate(BaseModel):
    product_id: str
    target_price_try: float = Field(gt=0, le=1_000_000)
    notify_email: bool = True
    notify_in_app: bool = True
    note: str = Field(default="", max_length=200)


class GamingWatchUpdate(BaseModel):
    target_price_try: float | None = Field(default=None, gt=0, le=1_000_000)
    notify_email: bool | None = None
    notify_in_app: bool | None = None
    note: str | None = Field(default=None, max_length=200)


class GamingWatch(BaseModel):
    id: str
    user_id: str
    product_id: str
    product_name: str
    game_slug: str
    game_name: str
    game_currency: str
    accent_color: str
    target_price_try: float
    current_price_try: float
    best_seller_name: str | None
    best_offer_id: str | None
    best_offer_url: str | None
    triggered: bool
    notify_email: bool
    notify_in_app: bool
    note: str
    last_notified_at: str | None
    created_at: str


# ---- Affiliate earnings --------------------------------------------------


class GamingEarningsBySeller(BaseModel):
    seller_id: str
    seller_name: str
    total_spent: float
    commission: float
    count: int


class GamingEarningsSummary(BaseModel):
    month: str
    month_label: str
    total_spent: float
    total_commission: float
    count: int
    by_seller: list[GamingEarningsBySeller]


# ---- Gaming budget (leverages existing budgets collection) --------------


class GamingBudgetStatus(BaseModel):
    month: str
    limit: float | None
    spent: float
    percent: float
    exceeded: bool
    warning: bool


class GamingBudgetSet(BaseModel):
    limit: float = Field(gt=0, le=1_000_000)
    month: str = Field(default="", max_length=7)


# ---- Catalog history / revert -------------------------------------------


class GamingCatalogHistoryEntry(BaseModel):
    id: str
    user_id: str
    offer_id: str
    product_id: str
    game_slug: str
    game_name: str
    product_name: str
    seller_id: str
    seller_name: str
    action: str  # override | modify | delete | bulk_import | reset
    before: dict | None
    after: dict | None
    changed_at: str


# ---- Earnings trend / affiliate report ----------------------------------


class GamingEarningsTrendPoint(BaseModel):
    month: str
    month_label: str
    total_spent: float
    total_commission: float
    count: int


class GamingEarningsTrend(BaseModel):
    months: int
    range_from: str
    range_to: str
    total_spent: float
    total_commission: float
    count: int
    points: list[GamingEarningsTrendPoint]
    by_seller: list[GamingEarningsBySeller]
