/**
 * Display-currency preference — TRY (default) / USD / EUR.
 *
 * Backend stores and computes every aggregate (dashboard summary, incomes,
 * expenses, bills, budgets) in TRY only; there is no per-user currency field
 * on the User model and no live FX integration anywhere in this app. The one
 * exchange-rate table that already existed (approximate, fixed) lived in two
 * places — `backend/lib/finance.py` and a duplicate literal in
 * `Subscriptions.tsx` — used only to fold a subscription's own USD/EUR price
 * into a TRY-denominated monthly total. This module mirrors that same
 * backend RATES table verbatim (single frontend source of truth now) and
 * reuses it for the reverse direction: converting a TRY aggregate into the
 * user's chosen display currency. No new/real FX system is introduced — the
 * conversion stays exactly as approximate as it already was, and every
 * converted value is prefixed with "≈" so it's never presented as exact.
 *
 * Context (like `i18n.tsx`), not an isolated per-component hook (like the
 * simpler `theme.ts`): several components mounted at once (sidebar, topbar,
 * every finance page under AppShell) must all re-render together the instant
 * the preference changes in Settings — a private `useState` per call site
 * would let them drift out of sync until a full remount.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { money } from "@/lib/format";

export type DisplayCurrency = "TRY" | "USD" | "EUR";

// Labels live in i18n (currency.try/usd/eur) rather than here, so the
// switcher UI can show them in the active language. This array is just the
// stable code+symbol pairs consumed alongside a t() call at each call site.
export const CURRENCIES: { code: DisplayCurrency; symbol: string }[] = [
  { code: "TRY", symbol: "₺" },
  { code: "USD", symbol: "$" },
  { code: "EUR", symbol: "€" },
];

// Verbatim copy of backend/lib/finance.py's RATES — keep the two in sync by hand
// if either changes; this is the only other place the constant is allowed to live.
export const RATES: Record<DisplayCurrency, number> = { TRY: 1, USD: 38, EUR: 41 };

// Any-currency amount -> TRY, same formula as backend's to_try().
export function toTry(amount: number, currency: string): number {
  return amount * (RATES[currency as DisplayCurrency] ?? 1);
}

// TRY amount -> the given display currency (inverse of toTry against TRY).
// Exported (not just used internally by useMoney().display) for the rare case
// — the dashboard trend chart — where a caller needs the converted *number*,
// not a formatted string, e.g. to feed a recharts dataset.
export function fromTry(amountTry: number, currency: DisplayCurrency): number {
  return currency === "TRY" ? amountTry : amountTry / RATES[currency];
}

const STORAGE_KEY = "subly.currency";

function readCurrency(): DisplayCurrency {
  if (typeof window === "undefined") return "TRY";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  return saved === "USD" || saved === "EUR" || saved === "TRY" ? saved : "TRY";
}

const CurrencyContext = createContext<{ currency: DisplayCurrency; setCurrency: (c: DisplayCurrency) => void }>({
  currency: "TRY",
  setCurrency: () => {},
});

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<DisplayCurrency>(() => readCurrency());

  useEffect(() => {
    try { window.localStorage.setItem(STORAGE_KEY, currency); } catch { /* ignore */ }
  }, [currency]);

  const value = useMemo(() => ({ currency, setCurrency: setCurrencyState }), [currency]);
  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency() {
  return useContext(CurrencyContext);
}

// For TRY-baseline aggregates only (dashboard/income/expense/budget/savings/bills
// totals). Never use this on a record that already carries its own `currency`
// field (a subscription's native price, a Deal, a calendar event) — those must
// keep showing their real, un-converted currency; converting them would distort
// what the user actually pays.
export function useMoney() {
  const { currency } = useCurrency();
  const display = (amountTry: number, fractions = 0): string => {
    const formatted = money(fromTry(amountTry, currency), currency, fractions);
    return currency === "TRY" ? formatted : `≈ ${formatted}`;
  };
  return { currency, display };
}
