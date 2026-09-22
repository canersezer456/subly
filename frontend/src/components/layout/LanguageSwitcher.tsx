import { useEffect, useRef, useState } from "react";
import { Globe } from "lucide-react";
import { LANGS, useT, type Lang } from "@/lib/i18n";

// Redesigned for 5 languages (tr/en/de/es/fr): name/code-based, not
// flag-primary — flags alone aren't a reliable language indicator (several
// languages share flags, several countries share languages). Desktop shows
// the full language name; mobile falls back to the compact 2-letter code,
// mirroring CurrencySwitcher's responsive pattern so the two sit consistently
// side by side in the topbar.
export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { lang, setLang, t } = useT();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const current = LANGS.find((l) => l.code === lang) ?? LANGS[0];

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground ${compact ? "h-8" : "h-9"}`}
        data-testid="language-switcher"
        aria-label={t("topbar.language")}
      >
        <Globe size={13} />
        <span className="hidden sm:inline">{current.label}</span>
        <span className="font-mono uppercase sm:hidden">{current.code}</span>
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-44 rounded-xl border border-border bg-popover p-1 shadow-2xl" data-testid="language-switcher-menu">
          {LANGS.map((option) => (
            <button
              key={option.code}
              type="button"
              onClick={() => { setLang(option.code as Lang); setOpen(false); }}
              className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${option.code === lang ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground"}`}
              data-testid={`language-option-${option.code}`}
            >
              <span>{option.label}</span>
              <span className="font-mono text-[10px] uppercase text-muted-foreground">{option.code}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
