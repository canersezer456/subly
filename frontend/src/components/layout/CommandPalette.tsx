import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { NAV_ITEMS } from "@/components/layout/AppShell";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";

// Lightweight Ctrl+K / Cmd+K command palette — no new dependency, built on the
// existing accessible Dialog primitive (focus trap + Escape already handled
// there) and the same NAV_ITEMS list the sidebar/bottom nav use. Search runs
// against t(item.key) so it matches whatever the currently active language
// displays, in all 5 supported languages.
export function CommandPalette() {
  const { t } = useT();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) setQuery("");
  }, [open]);

  const items = useMemo(
    () => NAV_ITEMS.map((item) => ({ ...item, label: t(item.key) })),
    [t],
  );
  const filtered = useMemo(() => {
    const q = query.trim().toLocaleLowerCase();
    if (!q) return items;
    return items.filter((item) => item.label.toLocaleLowerCase().includes(q));
  }, [items, query]);

  function go(to: string) {
    setOpen(false);
    navigate(to);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground"
        aria-label={t("commandPalette.open")}
        data-testid="command-palette-trigger"
      >
        <Search size={13} />
        <span className="hidden font-mono sm:inline">Ctrl K</span>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="top-[20%] max-w-lg -translate-y-0 gap-0 overflow-hidden border-border bg-card p-0 sm:max-w-lg" data-testid="command-palette">
          <DialogTitle className="sr-only">{t("commandPalette.open")}</DialogTitle>
          <div className="flex items-center gap-2 border-b border-border px-3">
            <Search size={15} className="shrink-0 text-muted-foreground" />
            <Input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("commandPalette.placeholder")}
              className="h-12 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
              data-testid="command-palette-input"
            />
          </div>
          <ul className="max-h-80 overflow-y-auto p-2" data-testid="command-palette-list">
            {filtered.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.to}>
                  <button
                    type="button"
                    onClick={() => go(item.to)}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                    data-testid={`command-palette-item-${item.to.slice(1)}`}
                  >
                    <Icon size={15} className="text-muted-foreground" />
                    {item.label}
                  </button>
                </li>
              );
            })}
            {filtered.length === 0 && (
              <li className="px-3 py-6 text-center text-xs text-muted-foreground" data-testid="command-palette-empty">
                {t("commandPalette.empty")}
              </li>
            )}
          </ul>
        </DialogContent>
      </Dialog>
    </>
  );
}
