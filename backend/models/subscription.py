from datetime import date
from pydantic import BaseModel, Field, field_validator

from lib.provider_catalog import PROVIDERS_BY_ID

CURRENCIES = {"TRY", "USD", "EUR"}
STATUSES = {"active", "cancelled", "expired", "paused"}
BILLING_CYCLES = "^(monthly|quarterly|yearly)$"
# Values a stored subscription can carry. Only "manual" can be set through the
# create endpoint; the others are assigned server-side when a discovery candidate
# is accepted. "legacy" is never stored — it is how rows created before source
# tracking are reported (see routers/subscriptions.py::_subscription).
SOURCES = ("manual", "email", "transaction", "import", "legacy")


class SubscriptionInput(BaseModel):
    @field_validator("renewal_date", check_fields=False)
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            date.fromisoformat(value)
        return value

    @field_validator("currency", check_fields=False)
    @classmethod
    def valid_currency(cls, value):
        if value is not None and value not in CURRENCIES:
            raise ValueError("Supported currencies: TRY, USD, EUR")
        return value

    @field_validator("status", check_fields=False)
    @classmethod
    def valid_status(cls, value):
        if value is not None and value not in STATUSES:
            raise ValueError("Invalid subscription status")
        return value

    @field_validator("provider_id", check_fields=False)
    @classmethod
    def known_provider(cls, value):
        if value is not None and value not in PROVIDERS_BY_ID:
            raise ValueError("Unknown provider")
        return value


class SubscriptionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=40)
    price: float = Field(gt=0, le=100000)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    renewal_date: str = Field(min_length=10, max_length=10)
    payment_method: str = Field(default="", max_length=60)
    cancellation_url: str = Field(default="https://www.google.com", max_length=500)
    source: str = Field(default="manual", max_length=20)
    billing_cycle: str = Field(default="monthly", pattern=BILLING_CYCLES)
    usage: str = Field(default="active", pattern="^(active|rarely|unused)$")


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    category: str | None = Field(default=None, min_length=2, max_length=40)
    price: float | None = Field(default=None, gt=0, le=100000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    renewal_date: str | None = Field(default=None, min_length=10, max_length=10)
    payment_method: str | None = Field(default=None, max_length=60)
    cancellation_url: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=30)
    billing_cycle: str | None = Field(default=None, pattern=BILLING_CYCLES)
    usage: str | None = Field(default=None, pattern="^(active|rarely|unused)$")
    provider_id: str | None = Field(default=None, max_length=60)
    plan: str | None = Field(default=None, max_length=60)
    note: str | None = Field(default=None, max_length=500)


class PriceHistoryEntry(BaseModel):
    price: float
    currency: str
    changed_at: str


class Subscription(SubscriptionCreate):
    id: str
    status: str = "active"
    created_at: str
    provider_id: str | None = None
    plan: str | None = None
    note: str = ""
    legacy: bool = False
    legacy_reviewed: bool = False
    candidate_id: str | None = None
    price_history: list[PriceHistoryEntry] = []


class SubscriptionCreateRequest(SubscriptionCreate, SubscriptionInput):
    status: str = Field(default="active", max_length=30)
    provider_id: str | None = Field(default=None, max_length=60)
    plan: str | None = Field(default=None, max_length=60)
    note: str = Field(default="", max_length=500)
    # Set by the client after the user saw the "possible duplicate" warning.
    confirm_duplicate: bool = False


class SubscriptionUpdateRequest(SubscriptionUpdate, SubscriptionInput):
    pass


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


# ---- Provider catalog ----------------------------------------------------


class ProviderPricing(BaseModel):
    status: str


class Provider(BaseModel):
    id: str
    family: str
    name: str
    category: str
    subscription_category: str
    aliases: list[str]
    plans: list[str]
    manage_url: str
    merchant_patterns: list[str]
    email_domains: list[str]
    email_keywords: list[str] = []
    email_keywords_required: bool = False
    one_off_purchases: bool = False
    default_currency: str | None = None
    pricing: ProviderPricing
    note: str | None = None


class DuplicateMatch(BaseModel):
    id: str
    name: str
    price: float | None = None
    currency: str = "TRY"
    status: str = "active"


# ---- Discovery -----------------------------------------------------------


class CandidateEvidence(BaseModel):
    type: str
    source: str
    summary: str
    observed_at: str
    merchant: str | None = None
    sender_domain: str | None = None
    signal: str | None = None
    count: int | None = None
    cadence: str | None = None
    first_seen: str | None = None


class DiscoveryCandidate(BaseModel):
    id: str
    provider_id: str | None = None
    provider_name: str
    alternatives: list[str] = []
    ambiguous: bool = False
    suggested_plan: str | None = None
    suggested_price: float | None = None
    currency: str | None = None
    billing_cycle: str | None = None
    renewal_date: str | None = None
    evidence_type: str
    evidence_source: str
    evidence: list[CandidateEvidence]
    evidence_types: list[str]
    confidence: float
    confidence_label: str
    explanation: str
    status: str
    possible_duplicates: list[DuplicateMatch] = []
    accepted_subscription_id: str | None = None
    created_at: str
    updated_at: str | None = None


class CandidateImportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500_000)


class CandidateImportResponse(BaseModel):
    parsed_transactions: int
    skipped_lines: int
    created: int
    merged: int
    skipped_rejected: int
    already_accepted: int
    candidates: list[DiscoveryCandidate]


class CandidateAcceptRequest(SubscriptionInput):
    """Everything the user confirms when turning a candidate into a subscription.
    Fields left empty fall back to the candidate's suggestion; price and renewal
    date must exist on one side or the other."""

    provider_id: str | None = Field(default=None, max_length=60)
    name: str | None = Field(default=None, min_length=2, max_length=80)
    plan: str | None = Field(default=None, max_length=60)
    price: float | None = Field(default=None, gt=0, le=100000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    billing_cycle: str | None = Field(default=None, pattern=BILLING_CYCLES)
    renewal_date: str | None = Field(default=None, min_length=10, max_length=10)
    payment_method: str = Field(default="", max_length=60)
    note: str = Field(default="", max_length=500)
    confirm_duplicate: bool = False


class CandidateAcceptResponse(BaseModel):
    candidate: DiscoveryCandidate
    subscription: Subscription


class EmailSyncSummary(BaseModel):
    partial: bool = False
    skipped: int = 0
    scanned: int
    matched: int
    created: int
    merged: int
    skipped_rejected: int = 0
    already_accepted: int = 0


class EmailAdapterStatus(BaseModel):
    id: str
    name: str
    configured: bool
    connected: bool
    # connected | available (configured, user not connected) | reauth_required | not_configured
    state: str
    scope: str
    connected_at: str | None = None
    last_sync_at: str | None = None
    last_sync: EmailSyncSummary | None = None


class TransactionAdapterStatus(BaseModel):
    id: str
    name: str
    configured: bool
    connected: bool
    state: str


class EmailSourceStatus(BaseModel):
    available: bool
    connected: bool
    state: str
    adapters: list[EmailAdapterStatus]


class EmailConnectResponse(BaseModel):
    authorization_url: str


class EmailSyncResponse(EmailSyncSummary):
    candidates: list["DiscoveryCandidate"] = []


class TransactionSourceStatus(BaseModel):
    available: bool
    connected: bool
    state: str
    adapters: list[TransactionAdapterStatus]


class ImportSourceStatus(BaseModel):
    available: bool = True
    connected: bool = True
    state: str = "ready"


class DiscoveryStatus(BaseModel):
    email: EmailSourceStatus
    transaction: TransactionSourceStatus
    manual_import: ImportSourceStatus
    pending_candidates: int


# ---- Insights -------------------------------------------------------------


class InsightUpcoming(BaseModel):
    id: str
    name: str
    date: str
    days_until: int
    amount: float
    currency: str
    billing_cycle: str


class InsightBucket(BaseModel):
    key: str
    count: int
    monthly_try: float


class InsightYearly(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    monthly_equivalent_try: float


class InsightPriceChange(BaseModel):
    id: str
    name: str
    previous_price: float
    current_price: float
    currency: str
    changed_at: str
    change_percent: float


class InsightOverlap(BaseModel):
    category: str
    label: str
    count: int
    names: list[str]
    monthly_try: float
    message: str


class SubscriptionInsights(BaseModel):
    active_count: int
    total_count: int
    monthly_total_try: float
    yearly_projection_try: float
    upcoming: list[InsightUpcoming]
    next_renewal: InsightUpcoming | None = None
    unused_count: int
    rarely_count: int
    unused_monthly_try: float
    by_category: list[InsightBucket]
    by_payment_method: list[InsightBucket]
    yearly_subscriptions: list[InsightYearly]
    price_changes: list[InsightPriceChange]
    overlaps: list[InsightOverlap]
    legacy_unreviewed: int
    rates: dict[str, float]
