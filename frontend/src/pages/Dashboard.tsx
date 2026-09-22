import { useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { ArrowDownRight, ArrowUpRight, Bot, CalendarDays, Coins, Gamepad2, PiggyBank, Receipt, RefreshCw, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { categoryLabel, dateLabel, money, percent, relativeDays } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { isOnboardingDismissed } from "@/lib/onboarding";
import { fromTry, useMoney } from "@/lib/currency";
import { useSummary, useGamingEarnings } from "@/hooks/useDashboardSummary";
import type { User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ProviderMark } from "@/components/brand/ProviderMark";
import { OnboardingChecklist } from "@/components/dashboard/OnboardingChecklist";
import { EmptyState, LevelPill, Panel, ProgressBar, StatCard } from "@/components/shared/ui-bits";

function DashboardSkeleton() {
  return (
    <div className="animate-pulse" data-testid="dashboard-loading">
      <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div className="space-y-2.5">
          <div className="h-3 w-40 rounded bg-muted" />
          <div className="h-8 w-64 rounded bg-muted" />
          <div className="h-4 w-80 max-w-full rounded bg-muted" />
        </div>
        <div className="flex gap-2"><div className="h-9 w-32 rounded-lg bg-muted" /><div className="h-9 w-36 rounded-lg bg-muted" /></div>
      </div>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <Card key={i} className="h-32 border-border bg-card p-5" />)}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-6"><Card className="h-64 border-border bg-card p-6" /><Card className="h-56 border-border bg-card p-6" /></div>
        <div className="space-y-6"><Card className="h-40 border-border bg-card p-6" /><Card className="h-32 border-border bg-card p-6" /><Card className="h-40 border-border bg-card p-6" /></div>
      </div>
    </div>
  );
}

function DashboardError({ onRetry, t }: { onRetry: () => void; t: (key: string) => string }) {
  return (
    <div className="py-16" data-testid="dashboard-error">
      <EmptyState
        title={t("dashboard.error.title")}
        description={t("dashboard.error.description")}
        action={<Button variant="outline" onClick={onRetry} data-testid="dashboard-retry-button"><RefreshCw size={14} /> {t("dashboard.error.retry")}</Button>}
        testId="dashboard-error-state"
      />
    </div>
  );
}

export default function Dashboard() {
  const user = useOutletContext<User>();
  const { data, isLoading, isError, refetch } = useSummary();
  const gamingEarnings = useGamingEarnings();
  const { t, lang } = useT();
  const { currency, display } = useMoney();
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => isOnboardingDismissed(user.user_id));
  const hour = new Date().getHours();
  const greeting = hour < 12 ? t("dashboard.greeting.morning") : hour < 18 ? t("dashboard.greeting.day") : t("dashboard.greeting.evening");

  if (isError) return <DashboardError onRetry={() => refetch()} t={t} />;
  if (isLoading || !data) return <DashboardSkeleton />;
  const hasData = data.income_total > 0 || data.expense_total > 0;
  const changeUp = data.expense_change_percent > 0;
  // Trend chart must respect the display-currency preference too — bars, axis
  // and tooltip all read from this converted copy, not the raw TRY points.
  const chartData = data.trend.map((pt) => ({ ...pt, income: fromTry(pt.income, currency), expense: fromTry(pt.expense, currency) }));
  const chartTick = (v: number) => (Math.abs(v) >= 1000 ? `${Math.round(v / 1000)}k` : String(Math.round(v)));
  // Values here are already display-currency (chartData), unlike useMoney().display()
  // which expects a raw TRY amount — format directly instead of converting twice.
  const chartMoney = (v: number) => (currency === "TRY" ? money(v, currency, 0) : `≈ ${money(v, currency, 2)}`);

  return (
    <div data-testid="dashboard-page">
      {!onboardingDismissed && <OnboardingChecklist userId={user.user_id} userName={user.name} data={data} onDismiss={() => setOnboardingDismissed(true)} />}
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
        <StatCard label={t("dashboard.kpi.income")} value={display(data.income_total)} detail={t("dashboard.kpi.incomeDetail")} icon={<Wallet size={17} />} tone="emerald" to="/incomes" testId="kpi-income" />
        <StatCard label={t("dashboard.kpi.expense")} value={display(data.expense_total)} icon={<ArrowDownRight size={17} />} tone="rose" to="/expenses" testId="kpi-expense"
          detail={data.last_month_expense ? <span className={changeUp ? "text-amber-500" : "text-emerald-500"}>{changeUp ? <TrendingUp size={12} className="mr-1 inline" /> : <TrendingDown size={12} className="mr-1 inline" />}{changeUp ? "+" : ""}{t("dashboard.kpi.expenseChange", { percent: data.expense_change_percent })}</span> : t("dashboard.kpi.expenseDetail")} />
        <StatCard label={t("dashboard.kpi.remaining")} value={display(data.remaining)} detail={data.remaining >= 0 ? t("dashboard.kpi.savingsRate", { rate: percent(data.savings_rate) }) : t("dashboard.kpi.remainingNegative")} icon={<ArrowUpRight size={17} />} tone={data.remaining >= 0 ? "cyan" : "amber"} testId="kpi-remaining" />
        <StatCard label={t("dashboard.kpi.savings")} value={display(data.potential_savings)} detail={t("dashboard.kpi.savingsDetail", { count: data.alerts_count })} icon={<PiggyBank size={17} />} tone="amber" to="/savings" testId="kpi-savings" />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-6">
          <Panel title={t("dashboard.upcoming.title")} description={t("dashboard.upcoming.description")} testId="upcoming-payments-card"
            action={<Button render={<Link to="/calendar" />} variant="ghost" size="sm" className="text-primary" data-testid="open-calendar-button"><CalendarDays size={14} /> {t("nav.calendar")}</Button>}>
            {data.upcoming.length === 0 ? <EmptyState title={t("dashboard.upcoming.empty.title")} description={t("dashboard.upcoming.empty.description")} testId="upcoming-empty" /> : (
              <ul className="divide-y divide-border">
                {data.upcoming.slice(0, 7).map((item) => (
                  <li key={`${item.kind}-${item.id}`} className="flex items-center gap-3 py-3" data-testid={`upcoming-item-${item.id}`}>
                    {item.kind === "subscription" ? <ProviderMark name={item.title} size="sm" /> : <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground"><Receipt size={16} /></span>}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium" data-testid={`upcoming-title-${item.id}`}>{item.title}</p>
                      <p className="text-xs text-muted-foreground">{categoryLabel(t, item.category)} · {dateLabel(item.date)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold" data-testid={`upcoming-amount-${item.id}`}>{money(item.amount, item.currency, 2)}</p>
                      <p className={`text-[11px] ${item.days_until <= 1 ? "text-amber-500" : "text-muted-foreground"}`} data-testid={`upcoming-when-${item.id}`}>{relativeDays(item.days_until, lang)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={t("dashboard.trend.title")} description={t("dashboard.trend.description")} testId="trend-card">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} barGap={4} barCategoryGap="28%">
                  <CartesianGrid vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                  <YAxis tickLine={false} axisLine={false} width={44} tick={{ fill: "var(--muted-foreground)", fontSize: 10 }} tickFormatter={chartTick} />
                  <Tooltip cursor={{ fill: "var(--accent)", opacity: 0.4 }} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} formatter={(value: number, name: string) => [chartMoney(value), name === "income" ? t("dashboard.trend.income") : t("dashboard.trend.expense")]} />
                  <Bar dataKey="income" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="expense" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title={t("dashboard.categories.title")} description={t("dashboard.categories.description")} testId="category-breakdown-card"
            action={<Button render={<Link to="/expenses" />} variant="ghost" size="sm" className="text-primary" data-testid="open-expenses-button">{t("dashboard.categories.detail")}</Button>}>
            {data.categories.length === 0 ? <EmptyState title={t("dashboard.categories.empty.title")} description={t("dashboard.categories.empty.description")} testId="categories-empty" /> : (
              <ul className="space-y-3.5">
                {data.categories.slice(0, 6).map((cat) => (
                  <li key={cat.category} data-testid={`category-row-${cat.category}`}>
                    <div className="mb-1.5 flex justify-between text-sm"><span>{categoryLabel(t, cat.category)}</span><span className="font-mono text-muted-foreground">{display(cat.amount)} <span className="text-xs">· {percent(cat.percent)}</span></span></div>
                    <ProgressBar percent={cat.percent} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={t("dashboard.subs.title")} description={t("dashboard.subs.description")} testId="subscription-summary-card"
            action={<Button render={<Link to="/subscriptions" />} variant="ghost" size="sm" className="text-primary" data-testid="open-subscriptions-button"><RefreshCw size={14} /> {t("dashboard.subs.manage")}</Button>}>
            <div className="grid grid-cols-2 gap-4">
              <div><p className="text-xs text-muted-foreground">{t("dashboard.subs.monthly")}</p><p className="mt-1 font-mono text-xl font-bold" data-testid="subscription-monthly-value">{display(data.subscription_monthly)}</p></div>
              <div><p className="text-xs text-muted-foreground">{t("dashboard.subs.yearly")}</p><p className="mt-1 font-mono text-xl font-bold" data-testid="subscription-yearly-value">{display(data.subscription_yearly)}</p></div>
            </div>
          </Panel>

          <Panel title={t("dashboard.budget.title")} testId="budget-summary-card" action={<Button render={<Link to="/budget" />} variant="ghost" size="sm" className="text-primary" data-testid="open-budget-button">{t("common.all")}</Button>}>
            {data.budgets.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="budget-empty-hint">{t("dashboard.budget.empty")} <Link to="/budget" className="text-primary underline-offset-2 hover:underline">{t("dashboard.budget.emptyLink")}</Link>.</p> : (
              <ul className="space-y-3">
                {data.budgets.slice(0, 4).map((b) => (
                  <li key={b.id} data-testid={`budget-row-${b.id}`}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span>{categoryLabel(t, b.category)}</span>
                      <span className="flex items-center gap-2 font-mono text-xs text-muted-foreground">{money(b.spent)} / {money(b.limit)}{b.exceeded && <LevelPill level="red">{t("budget.flag.exceeded")}</LevelPill>}</span>
                    </div>
                    <ProgressBar percent={b.percent} exceeded={b.exceeded} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          {gamingEarnings.data && gamingEarnings.data.count > 0 && (
            <Panel
              title={t("dashboard.gaming.title")}
              description={t("dashboard.gaming.description")}
              testId="gaming-earnings-card"
              action={<Button render={<Link to="/gaming" />} variant="ghost" size="sm" className="text-primary" data-testid="open-gaming-button"><Gamepad2 size={14} /> {t("nav.gaming")}</Button>}
            >
              <div className="flex items-baseline gap-2">
                <Coins size={16} className="text-emerald-500" />
                <p className="font-mono text-2xl font-bold text-foreground" data-testid="gaming-earnings-total">{money(gamingEarnings.data.total_commission, "TRY", 2)}</p>
              </div>
              <p className="mt-1 text-xs text-muted-foreground" data-testid="gaming-earnings-detail">
                {t("dashboard.gaming.detail", { count: gamingEarnings.data.count, spent: money(gamingEarnings.data.total_spent, "TRY", 0) })}
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
