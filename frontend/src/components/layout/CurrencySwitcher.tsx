import { useEffect, useRef, useState } from "react";
import { Coins } from "lucide-react";
import { CURRENCIES, useCurrency } from "@/lib/currency";
import { useT } from "@/lib/i18n";

// Mirrors LanguageSwitcher.tsx exactly (same popover/click-outside pattern,
// same sizing) so the two sit naturally side by side in the topbar. Reads the
// same CurrencyProvider context Settings uses, so a change here or in
// Settings is reflected in the other instantly — no separate state, no page
// reload, no new persistence mechanism (still localStorage via currency.tsx).
export function CurrencySwitcher({ compact = false }: { compact?: boolean }) {
  const { currency, setCurrency } = useCurrency();
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const current = CURRENCIES.find((c) => c.code === currency) ?? CURRENCIES[0];
  const label = (code: string) => t(`currency.${code.toLowerCase()}`);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground ${compact ? "h-8" : "h-9"}`}
        data-testid="currency-switcher"
        aria-label={t("topbar.currency")}
      >
        <Coins size={13} />
        <span className="hidden font-mono sm:inline">{current.symbol} {current.code}</span>
        <span className="font-mono sm:hidden">{current.symbol}</span>
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-40 rounded-xl border border-border bg-popover p-1 shadow-2xl" data-testid="currency-switcher-menu">
          {CURRENCIES.map((option) => (
            <button
              key={option.code}
              type="button"
              onClick={() => { setCurrency(option.code); setOpen(false); }}
              className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${option.code === currency ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground"}`}
              data-testid={`currency-option-${option.code}`}
            >
              <span className="font-mono">{option.symbol} {option.code}</span>
              <span className="truncate text-xs text-muted-foreground">{label(option.code)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
