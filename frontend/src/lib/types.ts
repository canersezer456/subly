export interface User {
  user_id: string;
  email: string;
  name: string;
  picture?: string | null;
}

export interface AuthResponse {
  user: User;
}

export interface AuthPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends AuthPayload {
  name: string;
}

// ---- Subscriptions (mirrors models/subscription.py) ----------------------

export interface SubscriptionPayload {
  name: string;
  category: string;
  price: number;
  currency: string;
  renewal_date: string;
  payment_method: string;
  cancellation_url: string;
  source?: string;
  billing_cycle: "monthly" | "yearly";
  usage: "active" | "rarely" | "unused";
}

export interface Subscription extends SubscriptionPayload {
  id: string;
  source: string;
  status: string;
  created_at: string;
}

export interface MockScanResponse {
  scan_id: string;
  mocked: boolean;
  detected: SubscriptionPayload[];
}

export interface Deal {
  id: string;
  title: string;
  provider: string;
  category: string;
  description: string;
  current_price: number;
  discounted_price: number;
  savings: number;
  currency: string;
  url: string;
  badge: string;
  discount_percent: number;
  featured: boolean;
  partner_status: string;
}

// ---- Finance records (mirrors models/finance.py) -------------------------

export type IncomeKind = "regular" | "one_time" | "extra";

export interface IncomePayload {
  source: string;
  amount: number;
  kind: IncomeKind;
  date: string;
  note: string;
}
export interface Income extends IncomePayload {
  id: string;
  created_at: string;
}

export interface ExpensePayload {
  title: string;
  amount: number;
  category: string;
  date: string;
  payment_method: string;
  note: string;
}
export interface Expense extends ExpensePayload {
  id: string;
  created_at: string;
}

export type BillFrequency = "monthly" | "bimonthly" | "quarterly" | "yearly" | "once";

export interface BillPayload {
  provider: string;
  bill_type: string;
  amount: number;
  due_date: string;
  frequency: BillFrequency;
  auto_pay: boolean;
  payment_method: string;
  bill_number: string;
  note: string;
}
export interface Bill extends BillPayload {
  id: string;
  status: "pending" | "paid";
  created_at: string;
}

export interface BudgetPayload {
  category: string;
  limit: number;
  month: string;
}
export interface Budget extends BudgetPayload {
  id: string;
  created_at: string;
}

// ---- Derived views --------------------------------------------------------

export interface UpcomingPayment {
  id: string;
  title: string;
  amount: number;
  currency: string;
  date: string;
  days_until: number;
  kind: "bill" | "subscription";
  category: string;
  status: string;
}

export interface CategorySpend {
  category: string;
  amount: number;
  percent: number;
}

export interface BudgetUsage {
  id: string;
  category: string;
  limit: number;
  spent: number;
  percent: number;
  exceeded: boolean;
  month: string;
}

export interface TrendPoint {
  month: string;
  label: string;
  expense: number;
  income: number;
}

export interface DashboardSummary {
  month: string;
  month_label: string;
  today: string;
  income_total: number;
  expense_total: number;
  remaining: number;
  savings_rate: number;
  last_month_expense: number;
  expense_change_percent: number;
  subscription_monthly: number;
  subscription_yearly: number;
  bills_total: number;
  upcoming: UpcomingPayment[];
  categories: CategorySpend[];
  budgets: BudgetUsage[];
  trend: TrendPoint[];
  potential_savings: number;
  alerts_count: number;
}

export interface CalendarEvent {
  id: string;
  date: string;
  title: string;
  amount: number;
  currency: string;
  kind: "bill" | "subscription" | "income";
  category: string;
  status: string;
}

export interface CalendarResponse {
  month: string;
  label: string;
  total_out: number;
  total_in: number;
  events: CalendarEvent[];
}

export interface SavingsInsight {
  id: string;
  level: "red" | "yellow" | "green";
  title: string;
  detail: string;
  amount: number;
  action_label: string;
  action_path: string;
}

export interface SavingsReport {
  total: number;
  insights: SavingsInsight[];
  unused_subscriptions: number;
}

export interface Alert {
  id: string;
  level: "info" | "warning" | "success";
  message: string;
  path: string;
}

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface AccountExport {
  exported_at: string;
  user: Record<string, unknown>;
  incomes: unknown[];
  expenses: unknown[];
  bills: unknown[];
  budgets: unknown[];
  subscriptions: unknown[];
  assistant_messages: unknown[];
  digest_prefs: unknown[];
}

// ---- Weekly digest (mirrors routers/digest.py) ----------------------------

export interface DigestPreferencesUpdate {
  enabled: boolean;
  weekday: number; // 0 = Pazartesi
  hour: number;
  reminders_enabled: boolean;
  reminder_hour: number;
}

export interface DigestPreferences extends DigestPreferencesUpdate {
  last_sent_at: string | null;
  last_reminder_date: string | null;
}

export interface ReminderPreview {
  due_count: number;
  total: number;
  subject?: string | null;
  html?: string | null;
}

export interface ReminderSendResult {
  sent_to: string;
  email_id: string | null;
  due_count: number;
}

export interface DigestPreview {
  subject: string;
  html: string;
}

export interface DigestSendResult {
  sent_to: string;
  email_id: string | null;
}

// ---- Gaming (mirrors models/gaming.py) -----------------------------------

export interface GamingSeller {
  id: string;
  name: string;
  domain: string;
  reliability: "verified" | "trusted" | "caution";
  delivery: string;
  return_policy: string;
  payment_methods: string[];
  note: string;
}

export interface GamingOffer {
  id: string;
  product_id: string;
  seller_id: string;
  seller_name: string;
  seller_reliability: "verified" | "trusted" | "caution";
  seller_domain: string;
  price_try: number;
  original_price_try: number | null;
  delivery: string;
  stock: string;
  verified: boolean;
  campaign: string | null;
  url: string;
  updated_at: string;
  has_override: boolean;
  estimated_commission_try: number;
}

export interface GamingProduct {
  id: string;
  game_slug: string;
  game_name: string;
  game_currency: string;
  name: string;
  amount: number;
  unit: string;
  description: string;
  tag: "popular" | "best_value" | "new" | null;
  icon: string;
  best_price_try: number | null;
  offer_count: number;
}

export interface GamingGame {
  slug: string;
  name: string;
  currency: string;
  category: string;
  accent_color: string;
  icon_url: string;
  tagline: string;
  popular: boolean;
  product_count: number;
  best_price_try: number | null;
}

export interface GamingGameDetail extends GamingGame {
  products: GamingProduct[];
}

export interface GamingProductDetail extends GamingProduct {
  offers: GamingOffer[];
}

export interface GamingDeal {
  offer_id: string;
  product_id: string;
  product_name: string;
  game_slug: string;
  game_name: string;
  game_currency: string;
  accent_color: string;
  price_try: number;
  original_price_try: number | null;
  discount_percent: number;
  seller_name: string;
  seller_reliability: "verified" | "trusted" | "caution";
  delivery: string;
  campaign: string | null;
  url: string;
}

export interface GamingHome {
  updated_at: string;
  catalog_note: string;
  popular_games: GamingGame[];
  all_games: GamingGame[];
  cheapest_offers: GamingDeal[];
  campaigns: GamingDeal[];
  instant_delivery: GamingDeal[];
  today_deals: GamingDeal[];
  sellers: GamingSeller[];
}

export interface GamingPurchasePayload {
  offer_id: string;
  product_id: string;
  seller_id: string;
  amount_try: number;
  payment_method?: string;
  note?: string;
  date?: string;
}

export interface GamingPurchase {
  id: string;
  user_id: string;
  offer_id: string;
  product_id: string;
  product_name: string;
  game_slug: string;
  game_name: string;
  seller_id: string;
  seller_name: string;
  amount_try: number;
  payment_method: string;
  date: string;
  note: string;
  expense_id: string;
  created_at: string;
  estimated_commission_try: number;
  commission_rate: number;
}

export interface GamingPurchaseResponse {
  purchase: GamingPurchase;
  monthly_total: number;
  monthly_count: number;
}

export interface GamingSummary {
  month: string;
  total: number;
  count: number;
  top_games: { game: string; amount: number }[];
}

export interface GamingSearchResponse {
  games: GamingGame[];
  products: GamingProduct[];
}

export interface GamingCatalogAdminRow {
  offer_id: string;
  product_id: string;
  game_slug: string;
  game_name: string;
  product_name: string;
  seller_id: string;
  seller_name: string;
  seller_reliability: "verified" | "trusted" | "caution";
  base_price_try: number;
  current_price_try: number;
  base_original_price_try: number | null;
  current_original_price_try: number | null;
  base_delivery: string;
  current_delivery: string;
  base_campaign: string | null;
  current_campaign: string | null;
  base_url: string;
  current_url: string;
  has_override: boolean;
  updated_at: string | null;
}

export interface GamingOfferOverrideInput {
  price_try?: number | null;
  original_price_try?: number | null;
  delivery?: string | null;
  campaign?: string | null;
  url?: string | null;
}

export interface GamingBulkImportRow {
  offer_id: string;
  price_try?: number | null;
  original_price_try?: number | null;
  delivery?: string | null;
  campaign?: string | null;
  url?: string | null;
}

export interface GamingBulkImport {
  overrides: GamingBulkImportRow[];
}

export interface GamingImportResult {
  applied: number;
  skipped: number;
  errors: string[];
}

export interface GamingWatchPayload {
  product_id: string;
  target_price_try: number;
  notify_email: boolean;
  notify_in_app: boolean;
  note?: string;
}

export interface GamingWatch {
  id: string;
  user_id: string;
  product_id: string;
  product_name: string;
  game_slug: string;
  game_name: string;
  game_currency: string;
  accent_color: string;
  target_price_try: number;
  current_price_try: number;
  best_seller_name: string | null;
  best_offer_id: string | null;
  best_offer_url: string | null;
  triggered: boolean;
  notify_email: boolean;
  notify_in_app: boolean;
  note: string;
  last_notified_at: string | null;
  created_at: string;
}

export interface GamingEarningsBySeller {
  seller_id: string;
  seller_name: string;
  total_spent: number;
  commission: number;
  count: number;
}

export interface GamingEarningsSummary {
  month: string;
  month_label: string;
  total_spent: number;
  total_commission: number;
  count: number;
  by_seller: GamingEarningsBySeller[];
}

export interface GamingBudgetStatus {
  month: string;
  limit: number | null;
  spent: number;
  percent: number;
  exceeded: boolean;
  warning: boolean;
}

export interface GamingBudgetSet {
  limit: number;
  month?: string;
}

export interface GamingCatalogHistoryEntry {
  id: string;
  user_id: string;
  offer_id: string;
  product_id: string;
  game_slug: string;
  game_name: string;
  product_name: string;
  seller_id: string;
  seller_name: string;
  action: "override" | "modify" | "delete" | "bulk_import" | "reset" | "revert";
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  changed_at: string;
}

export interface GamingEarningsTrendPoint {
  month: string;
  month_label: string;
  total_spent: number;
  total_commission: number;
  count: number;
}

export interface GamingEarningsTrend {
  months: number;
  range_from: string;
  range_to: string;
  total_spent: number;
  total_commission: number;
  count: number;
  points: GamingEarningsTrendPoint[];
  by_seller: GamingEarningsBySeller[];
}
