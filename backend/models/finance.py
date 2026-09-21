from pydantic import BaseModel, Field

# ---- Incomes -------------------------------------------------------------


class IncomeCreate(BaseModel):
    source: str = Field(min_length=2, max_length=80)
    amount: float = Field(gt=0, le=10_000_000)
    kind: str = Field(default="regular", pattern="^(regular|one_time|extra)$")
    date: str = Field(min_length=10, max_length=10)
    note: str = Field(default="", max_length=300)


class IncomeUpdate(BaseModel):
    source: str | None = Field(default=None, min_length=2, max_length=80)
    amount: float | None = Field(default=None, gt=0, le=10_000_000)
    kind: str | None = Field(default=None, pattern="^(regular|one_time|extra)$")
    date: str | None = Field(default=None, min_length=10, max_length=10)
    note: str | None = Field(default=None, max_length=300)


class Income(IncomeCreate):
    id: str
    created_at: str


# ---- Expenses ------------------------------------------------------------


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    amount: float = Field(gt=0, le=10_000_000)
    category: str = Field(min_length=2, max_length=40)
    date: str = Field(min_length=10, max_length=10)
    payment_method: str = Field(default="Kart •••• 4821", max_length=60)
    note: str = Field(default="", max_length=300)


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=80)
    amount: float | None = Field(default=None, gt=0, le=10_000_000)
    category: str | None = Field(default=None, min_length=2, max_length=40)
    date: str | None = Field(default=None, min_length=10, max_length=10)
    payment_method: str | None = Field(default=None, max_length=60)
    note: str | None = Field(default=None, max_length=300)


class Expense(ExpenseCreate):
    id: str
    created_at: str


# ---- Bills ---------------------------------------------------------------


class BillCreate(BaseModel):
    provider: str = Field(min_length=2, max_length=80)
    bill_type: str = Field(min_length=2, max_length=40)
    amount: float = Field(gt=0, le=10_000_000)
    due_date: str = Field(min_length=10, max_length=10)
    frequency: str = Field(default="monthly", pattern="^(monthly|bimonthly|quarterly|yearly|once)$")
    auto_pay: bool = False
    payment_method: str = Field(default="Havale / EFT", max_length=60)
    bill_number: str = Field(default="", max_length=60)
    note: str = Field(default="", max_length=300)


class BillUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=2, max_length=80)
    bill_type: str | None = Field(default=None, min_length=2, max_length=40)
    amount: float | None = Field(default=None, gt=0, le=10_000_000)
    due_date: str | None = Field(default=None, min_length=10, max_length=10)
    frequency: str | None = Field(default=None, pattern="^(monthly|bimonthly|quarterly|yearly|once)$")
    auto_pay: bool | None = None
    payment_method: str | None = Field(default=None, max_length=60)
    bill_number: str | None = Field(default=None, max_length=60)
    note: str | None = Field(default=None, max_length=300)
    status: str | None = Field(default=None, pattern="^(pending|paid)$")


class Bill(BillCreate):
    id: str
    status: str = "pending"
    created_at: str


# ---- Budgets -------------------------------------------------------------


class BudgetCreate(BaseModel):
    category: str = Field(min_length=2, max_length=40)
    limit: float = Field(gt=0, le=10_000_000)
    month: str = Field(default="", max_length=7)


class BudgetUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=40)
    limit: float | None = Field(default=None, gt=0, le=10_000_000)
    month: str | None = Field(default=None, max_length=7)


class Budget(BudgetCreate):
    id: str
    created_at: str


# ---- Derived / read-only views -----------------------------------------


class UpcomingPayment(BaseModel):
    id: str
    title: str
    amount: float
    currency: str = "TRY"
    date: str
    days_until: int
    kind: str  # bill | subscription
    category: str
    status: str


class CategorySpend(BaseModel):
    category: str
    amount: float
    percent: float


class BudgetUsage(BaseModel):
    id: str
    category: str
    limit: float
    spent: float
    percent: float
    exceeded: bool
    month: str


class TrendPoint(BaseModel):
    month: str
    label: str
    expense: float
    income: float


class DashboardSummary(BaseModel):
    month: str
    month_label: str
    today: str
    income_total: float
    expense_total: float
    remaining: float
    savings_rate: float
    last_month_expense: float
    expense_change_percent: float
    subscription_monthly: float
    subscription_yearly: float
    bills_total: float
    upcoming: list[UpcomingPayment]
    categories: list[CategorySpend]
    budgets: list[BudgetUsage]
    trend: list[TrendPoint]
    potential_savings: float
    alerts_count: int


class CalendarEvent(BaseModel):
    id: str
    date: str
    title: str
    amount: float
    currency: str = "TRY"
    kind: str  # bill | subscription | income
    category: str
    status: str


class CalendarResponse(BaseModel):
    month: str
    label: str
    total_out: float
    total_in: float
    events: list[CalendarEvent]


class SavingsInsight(BaseModel):
    id: str
    level: str  # red | yellow | green
    title: str
    detail: str
    amount: float
    action_label: str
    action_path: str


class SavingsReport(BaseModel):
    total: float
    insights: list[SavingsInsight]
    unused_subscriptions: int


class Alert(BaseModel):
    id: str
    level: str  # info | warning | success
    message: str
    path: str


class AssistantMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AccountExport(BaseModel):
    exported_at: str
    user: dict
    incomes: list[dict]
    expenses: list[dict]
    bills: list[dict]
    budgets: list[dict]
    subscriptions: list[dict]
    assistant_messages: list[dict]
    assistant_usage: list[dict] = []
    digest_prefs: list[dict] = []
