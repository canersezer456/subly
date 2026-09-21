export function money(value: number, currency = "TRY", fractions = 0) {
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency, minimumFractionDigits: fractions, maximumFractionDigits: fractions === 0 ? 0 : 2 }).format(value);
}

export function dateLabel(date: string, withYear = false) {
  return new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: withYear ? "long" : "short", ...(withYear ? { year: "numeric" } : {}) }).format(new Date(`${date}T12:00:00`));
}

export function relativeDays(days: number) {
  if (days === 0) return "Bugün";
  if (days === 1) return "Yarın";
  if (days < 0) return `${Math.abs(days)} gün gecikti`;
  return `${days} gün sonra`;
}

export function percent(value: number) {
  return `%${Math.round(value)}`;
}

export const EXPENSE_CATEGORIES = ["Market", "Restoran", "Ulaşım", "Alışveriş", "Eğlence", "Sağlık", "Eğitim", "Ev", "Faturalar", "Abonelikler", "Gaming", "Seyahat", "Diğer"];
export const BILL_TYPES = ["Elektrik", "Su", "Doğalgaz", "İnternet", "Telefon", "Kira", "TV / Yayın", "Sigorta", "Kredi / Borç", "Diğer"];
export const SUBSCRIPTION_CATEGORIES = ["Eğlence", "Müzik", "İş / Yazılım", "Bulut", "Oyun", "Spor", "Yapay Zekâ", "Diğer"];
export const PAYMENT_METHODS = ["Kart •••• 4821", "Kart •••• 1190", "Banka kartı", "Nakit", "Havale / EFT", "Otomatik ödeme"];

export const BILL_TYPE_ICONS: Record<string, string> = { Elektrik: "⚡", Su: "💧", Doğalgaz: "🔥", İnternet: "🌐", Telefon: "📱", Kira: "🏠", "TV / Yayın": "📺", Sigorta: "🛡️", "Kredi / Borç": "🏦", Diğer: "📋" };
export const FREQUENCY_LABELS: Record<string, string> = { monthly: "Aylık", bimonthly: "2 ayda bir", quarterly: "3 ayda bir", yearly: "Yıllık", once: "Tek seferlik" };
export const INCOME_KIND_LABELS: Record<string, string> = { regular: "Düzenli", one_time: "Tek seferlik", extra: "Ek gelir" };
export const USAGE_LABELS: Record<string, string> = { active: "Aktif kullanım", rarely: "Nadiren", unused: "Kullanılmıyor" };

export function todayIso() {
  // Display-only default for date inputs; the backend anchors all real "today" logic.
  return new Date().toISOString().slice(0, 10);
}

export function monthIso(date = new Date()) {
  return date.toISOString().slice(0, 7);
}
