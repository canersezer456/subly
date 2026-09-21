import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { Bell, Bot, CalendarDays, CreditCard, Gamepad2, Home, LayoutDashboard, LogOut, Menu, Moon, PiggyBank, Receipt, RefreshCw, Settings, Sun, Target, Wallet, X } from "lucide-react";
import { apiGet } from "@/lib/api";
import { endSession } from "@/lib/session";
import { useTheme } from "@/lib/theme";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { Alert, User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { LevelPill } from "@/components/shared/ui-bits";
import { SBrand } from "@/components/brand/SBrand";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";

export const NAV_ITEMS = [
  { to: "/dashboard", key: "nav.dashboard", icon: LayoutDashboard },
  { to: "/expenses", key: "nav.expenses", icon: CreditCard },
  { to: "/incomes", key: "nav.incomes", icon: Wallet },
  { to: "/subscriptions", key: "nav.subscriptions", icon: RefreshCw },
  { to: "/bills", key: "nav.bills", icon: Receipt },
  { to: "/calendar", key: "nav.calendar", icon: CalendarDays },
  { to: "/budget", key: "nav.budget", icon: Target },
  { to: "/savings", key: "nav.savings", icon: PiggyBank },
  { to: "/assistant", key: "nav.assistant", icon: Bot },
  { to: "/gaming", key: "nav.gaming", icon: Gamepad2 },
  { to: "/household", key: "nav.household", icon: Home },
  { to: "/settings", key: "nav.settings", icon: Settings },
];

const MOBILE_PRIMARY = ["/dashboard", "/expenses", "/subscriptions", "/gaming", "/assistant"];

export function useMe() {
  return useQuery({ queryKey: ["me"], queryFn: () => apiGet<User | null>("/auth/me"), retry: false, staleTime: 60_000 });
}

function Brand() {
  const { t } = useT();
  return (
    <Link to="/dashboard" className="flex items-center gap-2.5" data-testid="app-brand">
      <SBrand size={36} rounded="xl" className="shadow-lg shadow-primary/25" />
      <span>
        <span className="block font-heading text-base font-bold leading-none tracking-tight text-foreground">{t("brand.name")}</span>
        <span className="mt-0.5 block text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{t("brand.tagline")}</span>
      </span>
    </Link>
  );
}

function NavList({ onNavigate, compact = false }: { onNavigate?: () => void; compact?: boolean }) {
  const { t } = useT();
  return (
    <nav className="space-y-0.5" data-testid="sidebar-navigation">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink key={item.to} to={item.to} onClick={onNavigate} data-testid={`nav-${item.to.slice(1)}-link`}
            className={({ isActive }) => cn("flex items-center gap-3 rounded-lg px-3 text-sm transition-[background-color,color] duration-150", compact ? "py-2.5" : "py-2", isActive ? "bg-primary/12 font-medium text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground")}>
            <Icon size={17} />
            {t(item.key)}
          </NavLink>
        );
      })}
    </nav>
  );
}

function AlertsPopover({ alerts }: { alerts: Alert[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <Button variant="ghost" size="icon" onClick={() => setOpen((o) => !o)} className="relative text-muted-foreground" aria-label="Uyarılar" data-testid="alerts-button">
        <Bell size={17} />
        {alerts.length > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-amber-500 px-1 text-[9px] font-bold text-slate-950" data-testid="alerts-count">{alerts.length}</span>}
      </Button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-11 z-50 w-[22rem] max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-popover p-3 shadow-2xl" data-testid="alerts-panel">
            <div className="mb-2 flex items-center justify-between px-1">
              <p className="text-sm font-semibold">Akıllı uyarılar</p>
              <button type="button" onClick={() => setOpen(false)} className="text-muted-foreground" data-testid="alerts-close"><X size={14} /></button>
            </div>
            {alerts.length === 0 ? <p className="px-1 py-6 text-center text-xs text-muted-foreground" data-testid="alerts-empty">Şu an önemli bir uyarı yok. Her şey yolunda.</p> : (
              <ul className="max-h-80 space-y-1 overflow-y-auto">
                {alerts.map((alert) => (
                  <li key={alert.id}>
                    <Link to={alert.path} onClick={() => setOpen(false)} className="flex items-start gap-2 rounded-lg px-2 py-2 text-xs leading-relaxed hover:bg-accent" data-testid={`alert-item-${alert.id}`}>
                      <LevelPill level={alert.level}>{alert.level === "warning" ? "Dikkat" : alert.level === "success" ? "Fırsat" : "Bilgi"}</LevelPill>
                      <span className="text-foreground">{alert.message}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export function AppShell() {
  const me = useMe();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const { theme, toggle } = useTheme();
  const { t } = useT();
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: () => apiGet<Alert[]>("/alerts"), enabled: Boolean(me.data), retry: false });

  if (me.isLoading) return <div className="grid min-h-svh place-items-center bg-background text-sm text-muted-foreground" data-testid="auth-loading-state">{t("brand.loading")}</div>;
  if (!me.data) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  const user = me.data;
  const current = NAV_ITEMS.find((item) => location.pathname.startsWith(item.to));

  return (
    <div className="min-h-svh bg-background text-foreground" data-testid="subly-app">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-border bg-sidebar px-4 py-5 lg:flex" data-testid="sidebar">
        <Brand />
        <div className="mt-8 flex-1 overflow-y-auto"><NavList /></div>
        <div className="mt-4 rounded-xl border border-border bg-card/60 p-3" data-testid="sidebar-user-card">
          <div className="flex items-center gap-3">
            {user.picture ? <img src={user.picture} alt={user.name} className="h-9 w-9 rounded-full object-cover" /> : <span className="grid h-9 w-9 place-items-center rounded-full bg-primary/15 text-sm font-semibold text-primary">{user.name.slice(0, 1).toUpperCase()}</span>}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" data-testid="sidebar-user-name">{user.name}</p>
              <p className="truncate text-[11px] text-muted-foreground" data-testid="sidebar-user-email">{user.email}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => endSession("/")} className="mt-3 w-full justify-start text-muted-foreground hover:text-foreground" data-testid="logout-button"><LogOut size={14} /> {t("nav.logout")}</Button>
        </div>
      </aside>

      <div className="lg:pl-60">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-background/85 px-4 py-3 backdrop-blur-xl sm:px-6 lg:px-8" data-testid="topbar">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Menü" data-testid="mobile-menu-button"><Menu size={18} /></Button>
          <div className="lg:hidden"><Brand /></div>
          <p className="hidden text-sm text-muted-foreground lg:block" data-testid="topbar-breadcrumb">{t("brand.name")} <span className="mx-1.5 text-border">/</span> <span className="text-foreground">{current ? t(current.key) : ""}</span></p>
          <div className="ml-auto flex items-center gap-1">
            <LanguageSwitcher />
            <Button variant="ghost" size="icon" onClick={toggle} className="text-muted-foreground" aria-label="Temayı değiştir" data-testid="theme-toggle-button">{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</Button>
            <AlertsPopover alerts={alerts.data ?? []} />
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 pb-28 sm:px-6 lg:px-8 lg:py-8 lg:pb-12">
          <Outlet context={user} />
        </main>
      </div>

      <nav className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-6 rounded-2xl border border-border bg-card/95 p-1.5 shadow-2xl backdrop-blur-xl lg:hidden" data-testid="mobile-bottom-navigation">
        {NAV_ITEMS.filter((item) => MOBILE_PRIMARY.includes(item.to)).map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => cn("flex flex-col items-center gap-1 rounded-xl px-1 py-2 text-[9px]", isActive ? "bg-primary/12 text-primary" : "text-muted-foreground")} data-testid={`mobile-nav-${item.to.slice(1)}-link`}>
              <Icon size={17} /><span className="truncate">{t(item.key)}</span>
            </NavLink>
          );
        })}
        <button type="button" onClick={() => setMenuOpen(true)} className="flex flex-col items-center gap-1 rounded-xl px-1 py-2 text-[9px] text-muted-foreground" data-testid="mobile-nav-more-button"><Menu size={17} /><span>{t("nav.menu")}</span></button>
      </nav>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-72 border-border bg-sidebar p-5" data-testid="mobile-menu-sheet">
          <SheetTitle className="sr-only">{t("nav.menu")}</SheetTitle>
          <Brand />
          <div className="mt-6"><NavList onNavigate={() => setMenuOpen(false)} compact /></div>
          <Button variant="ghost" size="sm" onClick={() => endSession("/")} className="mt-6 w-full justify-start text-muted-foreground" data-testid="mobile-logout-button"><LogOut size={14} /> {t("nav.logout")}</Button>
        </SheetContent>
      </Sheet>
    </div>
  );
}
