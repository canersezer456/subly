import { useQuery } from "@tanstack/react-query";
import { Link, useOutletContext } from "react-router-dom";
import { ArrowDownRight, ArrowUpRight, Bot, CalendarDays, Coins, Gamepad2, PiggyBank, Receipt, RefreshCw, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "@/lib/api";
import { dateLabel, money, monthIso, percent, relativeDays } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { DashboardSummary, GamingEarningsSummary, User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ProviderMark } from "@/components/brand/ProviderMark";
import { EmptyState, LevelPill, Panel, ProgressBar, StatCard } from "@/components/shared/ui-bits";

export function useSummary() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => apiGet<DashboardSummary>("/dashboard/summary"), retry: false });
}

export function useGamingEarnings() {
  return useQuery({
    queryKey: ["gaming", "earnings", monthIso()],
    queryFn: () => apiGet<GamingEarningsSummary>(`/gaming/earnings?month=${monthIso()}`),
    retry: false,
    staleTime: 60_000,
  });
}

export default function Dashboard() {
  const user = useOutletContext<User>();
  const { data, isLoading } = useSummary();
  const gamingEarnings = useGamingEarnings();
  const { t } = useT();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? t("dashboard.greeting.morning") : hour < 18 ? t("dashboard.greeting.day") : t("dashboard.greeting.evening");

  if (isLoading || !data) return <div className="py-20 text-center text-sm text-muted-foreground" data-testid="dashboard-loading">Finansal görünüm hazırlanıyor…</div>;
  const hasData = data.income_total > 0 || data.expense_total > 0;
  const changeUp = data.expense_change_percent > 0;

  return (
    <div data-testid="dashboard-page">
      <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end" data-testid="dashboard-header">
        <div>
          <p className="mb-1.5 font-mono text-[11px] uppercase tracking-[0.2em] text-primary" data-testid="dashboard-eyebrow">{t("dashboard.eyebrow", { month: data.month_label })}</p>
          <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="dashboard-heading">{greeting}, {user.name.split(" ")[0]} 👋</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground" data-testid="dashboard-subtitle">
            {hasData
              ? (data.remaining >= 0 ? t("dashboard.subtitle.positive", { rate: percent(data.savings_rate) }) + " " : t("dashboard.subtitle.negative") + " ") + t("dashboard.subtitle.upcoming", { count: data.upcoming.length })
              : t("dashboard.subtitle.empty")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button render={<Link to="/expenses?new=1" />} variant="outline" data-testid="dashboard-add-expense-button">{t("dashboard.action.addExpense")}</Button>
          <Button render={<Link to="/assistant" />} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="dashboard-ask-assistant-button"><Bot size={15} /> {t("dashboard.action.askAssistant")}</Button>
        </div>
      </div>

      <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-testid="kpi-overview">
        <StatCard label="Gelir" value={money(data.income_total)} detail="Bu ay beklenen toplam gelir" icon={<Wallet size={17} />} tone="emerald" to="/incomes" testId="kpi-income" />
        <StatCard label="Gider" value={money(data.expense_total)} icon={<ArrowDownRight size={17} />} tone="rose" to="/expenses" testId="kpi-expense"
          detail={data.last_month_expense ? <span className={changeUp ? "text-amber-500" : "text-emerald-500"}>{changeUp ? <TrendingUp size={12} className="mr-1 inline" /> : <TrendingDown size={12} className="mr-1 inline" />}{changeUp ? "+" : ""}{data.expense_change_percent}% geçen aya göre</span> : "Faturalar ve abonelikler dahil"} />
        <StatCard label="Kalan" value={money(data.remaining)} detail={data.remaining >= 0 ? `Tasarruf oranı ${percent(data.savings_rate)}` : "Gider gelirin üzerinde"} icon={<ArrowUpRight size={17} />} tone={data.remaining >= 0 ? "cyan" : "amber"} testId="kpi-remaining" />
        <StatCard label="Tasarruf potansiyeli" value={money(data.potential_savings)} detail={`${data.alerts_count} akıllı uyarı`} icon={<PiggyBank size={17} />} tone="amber" to="/savings" testId="kpi-savings" />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-6">
          <Panel title="📅 Yaklaşan ödemeler" description="Önümüzdeki 30 gün · fatura ve abonelik yenilemeleri" testId="upcoming-payments-card"
            action={<Button render={<Link to="/calendar" />} variant="ghost" size="sm" className="text-primary" data-testid="open-calendar-button"><CalendarDays size={14} /> Takvim</Button>}>
            {data.upcoming.length === 0 ? <EmptyState title="Yaklaşan ödeme yok" description="Fatura veya abonelik ekleyince burada günlere göre sıralanır." testId="upcoming-empty" /> : (
              <ul className="divide-y divide-border">
                {data.upcoming.slice(0, 7).map((item) => (
                  <li key={`${item.kind}-${item.id}`} className="flex items-center gap-3 py-3" data-testid={`upcoming-item-${item.id}`}>
                    {item.kind === "subscription" ? <ProviderMark name={item.title} size="sm" /> : <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground"><Receipt size={16} /></span>}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium" data-testid={`upcoming-title-${item.id}`}>{item.title}</p>
                      <p className="text-xs text-muted-foreground">{item.category} · {dateLabel(item.date)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold" data-testid={`upcoming-amount-${item.id}`}>{money(item.amount, item.currency, 2)}</p>
                      <p className={`text-[11px] ${item.days_until <= 1 ? "text-amber-500" : "text-muted-foreground"}`} data-testid={`upcoming-when-${item.id}`}>{relativeDays(item.days_until)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Son 6 ay" description="Gelir ve gider karşılaştırması" testId="trend-card">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.trend} barGap={4} barCategoryGap="28%">
                  <CartesianGrid vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                  <YAxis tickLine={false} axisLine={false} width={44} tick={{ fill: "var(--muted-foreground)", fontSize: 10 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                  <Tooltip cursor={{ fill: "var(--accent)", opacity: 0.4 }} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} formatter={(value: number, name: string) => [money(value), name === "income" ? "Gelir" : "Gider"]} />
                  <Bar dataKey="income" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="expense" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Bu ay harcamaların" description="Kategorilere göre dağılım" testId="category-breakdown-card"
            action={<Button render={<Link to="/expenses" />} variant="ghost" size="sm" className="text-primary" data-testid="open-expenses-button">Detay</Button>}>
            {data.categories.length === 0 ? <EmptyState title="Henüz harcama yok" description="İlk harcamanı ekleyince dağılım burada görünür." testId="categories-empty" /> : (
              <ul className="space-y-3.5">
                {data.categories.slice(0, 6).map((cat) => (
                  <li key={cat.category} data-testid={`category-row-${cat.category}`}>
                    <div className="mb-1.5 flex justify-between text-sm"><span>{cat.category}</span><span className="font-mono text-muted-foreground">{money(cat.amount)} <span className="text-xs">· {percent(cat.percent)}</span></span></div>
                    <ProgressBar percent={cat.percent} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Abonelikler" description="Aktif servislerin sabit maliyeti" testId="subscription-summary-card"
            action={<Button render={<Link to="/subscriptions" />} variant="ghost" size="sm" className="text-primary" data-testid="open-subscriptions-button"><RefreshCw size={14} /> Yönet</Button>}>
            <div className="grid grid-cols-2 gap-4">
              <div><p className="text-xs text-muted-foreground">Aylık</p><p className="mt-1 font-mono text-xl font-bold" data-testid="subscription-monthly-value">{money(data.subscription_monthly)}</p></div>
              <div><p className="text-xs text-muted-foreground">Yıllık</p><p className="mt-1 font-mono text-xl font-bold" data-testid="subscription-yearly-value">{money(data.subscription_yearly)}</p></div>
            </div>
          </Panel>

          <Panel title="🎯 Bütçe durumu" testId="budget-summary-card" action={<Button render={<Link to="/budget" />} variant="ghost" size="sm" className="text-primary" data-testid="open-budget-button">Tümü</Button>}>
            {data.budgets.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="budget-empty-hint">Henüz bütçe tanımlamadın. <Link to="/budget" className="text-primary underline-offset-2 hover:underline">Aylık limit belirle</Link>.</p> : (
              <ul className="space-y-3">
                {data.budgets.slice(0, 4).map((b) => (
                  <li key={b.id} data-testid={`budget-row-${b.id}`}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span>{b.category}</span>
                      <span className="flex items-center gap-2 font-mono text-xs text-muted-foreground">{money(b.spent)} / {money(b.limit)}{b.exceeded && <LevelPill level="red">⚠️ Aşıldı</LevelPill>}</span>
                    </div>
                    <ProgressBar percent={b.percent} exceeded={b.exceeded} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          {gamingEarnings.data && gamingEarnings.data.count > 0 && (
            <Panel
              title="🎮 Gaming affiliate"
              description="Satıcı linklerinden bu ay tahmini kazanç"
              testId="gaming-earnings-card"
              action={<Button render={<Link to="/gaming" />} variant="ghost" size="sm" className="text-primary" data-testid="open-gaming-button"><Gamepad2 size={14} /> Gaming</Button>}
            >
              <div className="flex items-baseline gap-2">
                <Coins size={16} className="text-emerald-500" />
                <p className="font-mono text-2xl font-bold text-foreground" data-testid="gaming-earnings-total">{money(gamingEarnings.data.total_commission, "TRY", 2)}</p>
              </div>
              <p className="mt-1 text-xs text-muted-foreground" data-testid="gaming-earnings-detail">
                {gamingEarnings.data.count} satın alma · toplam harcama {money(gamingEarnings.data.total_spent, "TRY", 0)}
              </p>
              {gamingEarnings.data.by_seller.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {gamingEarnings.data.by_seller.slice(0, 3).map((row) => (
                    <li key={row.seller_id} className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-1.5 text-xs" data-testid={`gaming-earnings-seller-${row.seller_id}`}>
                      <span className="truncate text-muted-foreground">{row.seller_name}</span>
                      <span className="font-mono font-semibold text-emerald-500">+{money(row.commission, "TRY", 2)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
