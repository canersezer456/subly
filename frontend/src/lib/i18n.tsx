/**
 * Minimal i18n: TR (default) + EN. Context stores current lang, persists to localStorage,
 * updates <html lang>. `useT()` returns a translator `t(key)` that falls back to the key
 * if a translation is missing. Scope: sidebar, login/home, dashboard header, gaming hub.
 * Diğer ekranlar kademeli olarak eklenir; eksik anahtarlar mevcut Türkçe metni etkilemez.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Lang = "tr" | "en";

export const LANGS: { code: Lang; label: string; flag: string }[] = [
  { code: "tr", label: "Türkçe", flag: "🇹🇷" },
  { code: "en", label: "English", flag: "🇬🇧" },
];

type Dict = Record<string, string>;

const STRINGS: Record<Lang, Dict> = {
  tr: {
    // brand + tagline
    "brand.name": "Subly",
    "brand.tagline": "Finans işletim sistemi",
    "brand.loading": "Subly yükleniyor…",

    // auth / home
    "auth.eyebrow": "Subly · Finans işletim sistemi",
    "auth.headline.a": "Ekonomini",
    "auth.headline.b": "sen yönet",
    "auth.description": "Gelir, gider, abonelik, fatura ve bütçeni tek panelden yönet. Yaklaşan ödemeleri kaçırma, gereksiz harcamayı gör, nereden tasarruf edebileceğini öğren.",
    "auth.benefits.calendar.title": "Ödeme takvimi",
    "auth.benefits.calendar.desc": "Fatura ve yenilemeleri tek bakışta gör",
    "auth.benefits.savings.title": "Tasarruf motoru",
    "auth.benefits.savings.desc": "Kullanılmayan abonelik ve bütçe aşımlarını yakala",
    "auth.benefits.privacy.title": "Gizlilik önce",
    "auth.benefits.privacy.desc": "Şifreler hash'lenir, veriler istediğinde dışa aktarılır veya silinir",
    "auth.card.login": "Tekrar hoş geldin",
    "auth.card.register": "Subly'a katıl",
    "auth.card.description": "Finansal netlik birkaç saniye uzağında.",
    "auth.tab.login": "Giriş yap",
    "auth.tab.register": "Kayıt ol",
    "auth.field.name": "Adın",
    "auth.field.email": "E-posta adresin",
    "auth.field.password": "Şifren (en az 8 karakter)",
    "auth.submit.login": "Güvenli giriş yap",
    "auth.submit.register": "Ücretsiz hesap oluştur",
    "auth.submit.busy": "Bağlanıyor…",
    "auth.divider": "veya",
    "auth.google": "Google ile güvenli devam et",
    "auth.demo": "Demo hesabını doldur",
    "auth.security": "Şifren güvenli şekilde hash'lenir; oturum httpOnly çerezle korunur. Banka/e-posta taraması ilk sürümde SİMÜLASYON'dur.",
    "auth.error.login": "E-posta veya şifre hatalı. Demo bilgilerini doldurup tekrar dene.",
    "auth.error.register": "Bu e-posta zaten kayıtlı olabilir veya bilgiler eksik (şifre en az 8 karakter).",

    // sidebar / nav
    "nav.dashboard": "Panel",
    "nav.expenses": "Harcamalar",
    "nav.incomes": "Gelirler",
    "nav.subscriptions": "Abonelikler",
    "nav.bills": "Faturalar",
    "nav.calendar": "Takvim",
    "nav.budget": "Bütçe",
    "nav.savings": "Tasarruf",
    "nav.assistant": "AI Asistan",
    "nav.gaming": "Gaming",
    "nav.household": "Ev",
    "nav.settings": "Ayarlar",
    "nav.logout": "Güvenli çıkış",
    "nav.menu": "Menü",
    "topbar.language": "Dil",

    // dashboard header
    "dashboard.eyebrow": "{month} · finansal durumun",
    "dashboard.greeting.morning": "Günaydın",
    "dashboard.greeting.day": "İyi günler",
    "dashboard.greeting.evening": "İyi akşamlar",
    "dashboard.subtitle.positive": "Bu ay gelirinin {rate}'i elinde kalıyor.",
    "dashboard.subtitle.negative": "Bu ay giderin gelirini aşıyor.",
    "dashboard.subtitle.upcoming": "Önümüzdeki 30 günde {count} ödemen var.",
    "dashboard.subtitle.empty": "Gelir ve giderlerini ekleyerek başla; Subly geri kalanını hesaplar.",
    "dashboard.action.addExpense": "Harcama ekle",
    "dashboard.action.askAssistant": "Asistana sor",

    // gaming hub header
    "gaming.eyebrow": "Gaming",
    "gaming.title": "Ne satın almak istiyorsun?",
    "gaming.description": "Türkiye'nin güvenilir oyun marketlerini tek yerde karşılaştır. Onaylı satıcılar önce, en uygun fiyat en üstte.",
    "gaming.catalog.button": "Katalog düzenle",
    "gaming.earnings.button": "Kazanç raporu",
    "gaming.catalog.updated": "Katalog güncel · {date}",
  },
  en: {
    "brand.name": "Subly",
    "brand.tagline": "Finance operating system",
    "brand.loading": "Loading Subly…",

    "auth.eyebrow": "Subly · Finance OS",
    "auth.headline.a": "Own",
    "auth.headline.b": "your money",
    "auth.description": "Manage income, expenses, subscriptions, bills and budgets from one dashboard. Never miss a due date, see waste at a glance, and know exactly where to save.",
    "auth.benefits.calendar.title": "Payment calendar",
    "auth.benefits.calendar.desc": "Bills and renewals in one clean view",
    "auth.benefits.savings.title": "Savings engine",
    "auth.benefits.savings.desc": "Catches unused subs and budget overruns",
    "auth.benefits.privacy.title": "Privacy first",
    "auth.benefits.privacy.desc": "Hashed passwords, export or wipe your data anytime",
    "auth.card.login": "Welcome back",
    "auth.card.register": "Join Subly",
    "auth.card.description": "Financial clarity, a few seconds away.",
    "auth.tab.login": "Sign in",
    "auth.tab.register": "Create account",
    "auth.field.name": "Your name",
    "auth.field.email": "Your email",
    "auth.field.password": "Password (8+ characters)",
    "auth.submit.login": "Secure sign in",
    "auth.submit.register": "Create free account",
    "auth.submit.busy": "Connecting…",
    "auth.divider": "or",
    "auth.google": "Continue securely with Google",
    "auth.demo": "Fill demo credentials",
    "auth.security": "Passwords are hashed; sessions live in an httpOnly cookie. Bank / email scanning is SIMULATED in v1.",
    "auth.error.login": "Email or password looks wrong. Try the demo credentials to explore.",
    "auth.error.register": "That email may already exist or the form is incomplete (password 8+ characters).",

    "nav.dashboard": "Dashboard",
    "nav.expenses": "Expenses",
    "nav.incomes": "Income",
    "nav.subscriptions": "Subscriptions",
    "nav.bills": "Bills",
    "nav.calendar": "Calendar",
    "nav.budget": "Budget",
    "nav.savings": "Savings",
    "nav.assistant": "AI Assistant",
    "nav.gaming": "Gaming",
    "nav.household": "Home",
    "nav.settings": "Settings",
    "nav.logout": "Sign out",
    "nav.menu": "Menu",
    "topbar.language": "Language",

    "dashboard.eyebrow": "{month} · your money right now",
    "dashboard.greeting.morning": "Good morning",
    "dashboard.greeting.day": "Good afternoon",
    "dashboard.greeting.evening": "Good evening",
    "dashboard.subtitle.positive": "You're keeping {rate} of what came in.",
    "dashboard.subtitle.negative": "You're spending more than you earn this month.",
    "dashboard.subtitle.upcoming": "{count} payments due in the next 30 days.",
    "dashboard.subtitle.empty": "Add your income and expenses and Subly does the math.",
    "dashboard.action.addExpense": "Add expense",
    "dashboard.action.askAssistant": "Ask assistant",

    "gaming.eyebrow": "Gaming",
    "gaming.title": "What do you want to buy?",
    "gaming.description": "Compare Turkey's trusted game marketplaces in one place. Verified sellers first, cheapest offer on top.",
    "gaming.catalog.button": "Edit catalog",
    "gaming.earnings.button": "Earnings report",
    "gaming.catalog.updated": "Catalog fresh · {date}",
  },
};

const I18nContext = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (key: string, vars?: Record<string, string | number>) => string }>({
  lang: "tr",
  setLang: () => {},
  t: (key) => key,
});

const STORAGE_KEY = "subly.lang";

export function readLang(): Lang {
  if (typeof window === "undefined") return "tr";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved === "tr" || saved === "en") return saved;
  const browser = (window.navigator.language || "").slice(0, 2).toLowerCase();
  return browser === "en" ? "en" : "tr";
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_m, k) => (vars[k] !== undefined ? String(vars[k]) : `{${k}}`));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => readLang());

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  const setLang = (next: Lang) => {
    setLangState(next);
    try { window.localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
  };

  const value = useMemo(() => ({
    lang,
    setLang,
    t: (key: string, vars?: Record<string, string | number>) => {
      const dict = STRINGS[lang] ?? STRINGS.tr;
      const raw = dict[key] ?? STRINGS.tr[key] ?? key;
      return interpolate(raw, vars);
    },
  }), [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT() {
  return useContext(I18nContext);
}
