// Number/date formatting locale, driven by the active i18n language (see
// I18nProvider in lib/i18n.tsx, which calls setFormatLocale() on every
// language change). Module-level rather than a parameter on every call site:
// money()/dateLabel() are called from 50+ places across the app, and a
// locale parameter would mean threading the current language through every
// one of them. Since every consumer already re-renders on language change
// (via useT()'s context), this reactively updates their formatted output on
// the next render with zero call-site changes.
const LOCALE_BY_LANG: Record<string, string> = { tr: "tr-TR", en: "en-US", de: "de-DE", es: "es-ES", fr: "fr-FR" };
let currentLocale = "tr-TR";

export function setFormatLocale(lang: string) {
  currentLocale = LOCALE_BY_LANG[lang] ?? "en-US";
}

export function money(value: number, currency = "TRY", fractions = 0) {
  return new Intl.NumberFormat(currentLocale, { style: "currency", currency, minimumFractionDigits: fractions, maximumFractionDigits: fractions === 0 ? 0 : 2 }).format(value);
}

export function dateLabel(date: string, withYear = false) {
  return new Intl.DateTimeFormat(currentLocale, { day: "numeric", month: withYear ? "long" : "short", ...(withYear ? { year: "numeric" } : {}) }).format(new Date(`${date}T12:00:00`));
}

// `lang` defaults to "tr" for the few call sites that predate i18n; pass the
// current language explicitly (via useT()) wherever the surrounding UI is translated.
export function relativeDays(days: number, lang: "tr" | "en" | "de" | "es" | "fr" = "tr") {
  if (lang === "en") {
    if (days === 0) return "Today";
    if (days === 1) return "Tomorrow";
    if (days < 0) return `${Math.abs(days)} days late`;
    return `${days} days left`;
  }
  if (lang === "de") {
    if (days === 0) return "Heute";
    if (days === 1) return "Morgen";
    if (days < 0) return `${Math.abs(days)} Tage überfällig`;
    return `noch ${days} Tage`;
  }
  if (lang === "es") {
    if (days === 0) return "Hoy";
    if (days === 1) return "Mañana";
    if (days < 0) return `${Math.abs(days)} días de retraso`;
    return `${days} días restantes`;
  }
  if (lang === "fr") {
    if (days === 0) return "Aujourd'hui";
    if (days === 1) return "Demain";
    if (days < 0) return `${Math.abs(days)} jours de retard`;
    return `${days} jours restants`;
  }
  if (days === 0) return "Bugün";
  if (days === 1) return "Yarın";
  if (days < 0) return `${Math.abs(days)} gün gecikti`;
  return `${days} gün sonra`;
}

export function percent(value: number) {
  return `%${Math.round(value)}`;
}

// These arrays ARE the stored value — an expense's `category` field literally
// equals "Market" in the DB, and the backend's budget-vs-category matching
// compares these exact strings. Never change these values or migrate stored
// data; the *Label()/*translatedOpts helpers below only change what's shown
// on screen, never what's stored, posted, or matched.
export const EXPENSE_CATEGORIES = ["Market", "Restoran", "Ulaşım", "Alışveriş", "Eğlence", "Sağlık", "Eğitim", "Ev", "Faturalar", "Abonelikler", "Gaming", "Seyahat", "Diğer"];
export const BILL_TYPES = ["Elektrik", "Su", "Doğalgaz", "İnternet", "Telefon", "Kira", "TV / Yayın", "Sigorta", "Kredi / Borç", "Diğer"];
export const SUBSCRIPTION_CATEGORIES = ["Eğlence", "Müzik", "İş / Yazılım", "Bulut", "Oyun", "Spor", "Yapay Zekâ", "Diğer"];
export const PAYMENT_METHODS = ["Kart •••• 4821", "Kart •••• 1190", "Banka kartı", "Nakit", "Havale / EFT", "Otomatik ödeme"];

export const BILL_TYPE_ICONS: Record<string, string> = { Elektrik: "⚡", Su: "💧", Doğalgaz: "🔥", İnternet: "🌐", Telefon: "📱", Kira: "🏠", "TV / Yayın": "📺", Sigorta: "🛡️", "Kredi / Borç": "🏦", Diğer: "📋" };

// Kept as plain Turkish-value records because a few call sites still use them
// as a stable list of valid codes/values (e.g. iterating keys, defaulting a
// form field). Prefer the *Label() functions below for anything user-visible.
export const FREQUENCY_LABELS: Record<string, string> = { monthly: "Aylık", bimonthly: "2 ayda bir", quarterly: "3 ayda bir", yearly: "Yıllık", once: "Tek seferlik" };
export const INCOME_KIND_LABELS: Record<string, string> = { regular: "Düzenli", one_time: "Tek seferlik", extra: "Ek gelir" };
export const USAGE_LABELS: Record<string, string> = { active: "Aktif kullanım", rarely: "Nadiren", unused: "Kullanılmıyor" };

type Translate = (key: string) => string;

// Already code-keyed (monthly/regular/active, ...) — the safe, direct case:
// stored value is the code, i18n key is derived from the code, no lookup table needed.
const FREQUENCY_KEY: Record<string, string> = { monthly: "enum.frequency.monthly", bimonthly: "enum.frequency.bimonthly", quarterly: "enum.frequency.quarterly", yearly: "enum.frequency.yearly", once: "enum.frequency.once" };
const INCOME_KIND_KEY: Record<string, string> = { regular: "enum.incomeKind.regular", one_time: "enum.incomeKind.oneTime", extra: "enum.incomeKind.extra" };
const USAGE_KEY: Record<string, string> = { active: "enum.usage.active", rarely: "enum.usage.rarely", unused: "enum.usage.unused" };

export function frequencyLabel(t: Translate, code: string): string {
  const key = FREQUENCY_KEY[code];
  return key ? t(key) : code;
}
export function incomeKindLabel(t: Translate, code: string): string {
  const key = INCOME_KIND_KEY[code];
  return key ? t(key) : code;
}
export function usageLabel(t: Translate, code: string): string {
  const key = USAGE_KEY[code];
  return key ? t(key) : code;
}

// Freeform Turkish strings with no separate code — these ARE the stored
// value, so the lookup is by literal string, and any value with no match
// (custom/future category) falls back to itself, unchanged, so nothing ever
// breaks or shows a raw i18n key on screen.
const CATEGORY_KEY: Record<string, string> = { Market: "category.market", Restoran: "category.restaurant", Ulaşım: "category.transport", Alışveriş: "category.shopping", Eğlence: "category.entertainment", Sağlık: "category.health", Eğitim: "category.education", Ev: "category.home", Faturalar: "category.bills", Abonelikler: "category.subscriptions", Gaming: "category.gaming", Seyahat: "category.travel", Diğer: "category.other" };
const BILL_TYPE_KEY: Record<string, string> = { Elektrik: "billType.electricity", Su: "billType.water", Doğalgaz: "billType.naturalGas", İnternet: "billType.internet", Telefon: "billType.phone", Kira: "billType.rent", "TV / Yayın": "billType.tvStreaming", Sigorta: "billType.insurance", "Kredi / Borç": "billType.loanDebt", Diğer: "billType.other" };
const SUBSCRIPTION_CATEGORY_KEY: Record<string, string> = { Eğlence: "subCategory.entertainment", Müzik: "subCategory.music", "İş / Yazılım": "subCategory.workSoftware", Bulut: "subCategory.cloud", Oyun: "subCategory.gaming", Spor: "subCategory.sports", "Yapay Zekâ": "subCategory.ai", Diğer: "subCategory.other" };
const PAYMENT_METHOD_KEY: Record<string, string> = { "Kart •••• 4821": "paymentMethod.card1", "Kart •••• 1190": "paymentMethod.card2", "Banka kartı": "paymentMethod.debitCard", Nakit: "paymentMethod.cash", "Havale / EFT": "paymentMethod.wireTransfer", "Otomatik ödeme": "paymentMethod.autoPay" };

export function categoryLabel(t: Translate, value: string): string {
  const key = CATEGORY_KEY[value];
  return key ? t(key) : value;
}
export function billTypeLabel(t: Translate, value: string): string {
  const key = BILL_TYPE_KEY[value];
  return key ? t(key) : value;
}
export function subscriptionCategoryLabel(t: Translate, value: string): string {
  const key = SUBSCRIPTION_CATEGORY_KEY[value];
  return key ? t(key) : value;
}
export function paymentMethodLabel(t: Translate, value: string): string {
  const key = PAYMENT_METHOD_KEY[value];
  return key ? t(key) : value;
}

export function todayIso() {
  // Display-only default for date inputs; the backend anchors all real "today" logic.
  return new Date().toISOString().slice(0, 10);
}

export function monthIso(date = new Date()) {
  return date.toISOString().slice(0, 7);
}
