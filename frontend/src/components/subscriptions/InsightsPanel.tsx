import { CalendarClock, CreditCard, Info, Layers3, TrendingDown, TrendingUp } from "lucide-react";
import { dateLabel, money, paymentMethodLabel, subscriptionCategoryLabel } from "@/lib/format";
import { useMoney } from "@/lib/currency";
import type { SubscriptionInsights } from "@/lib/types";
import { Panel } from "@/components/shared/ui-bits";
import type { Translate } from "@/lib/subscriptionUi";

function Section({ title, icon, children, testId }: { title: string; icon: React.ReactNode; children: React.ReactNode; testId: string }) {
  return (
    <div className="space-y-2" data-testid={testId}>
      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{icon}{title}</p>
      {children}
    </div>
  );
}

/** Everything here is derived server-side from the caller's own subscriptions only. */
export function InsightsPanel({ insights, t }: { insights: SubscriptionInsights; t: Translate }) {
  const { display } = useMoney();
  const when = (days: number) => (days === 0 ? t("subsHub.insights.today") : t("subsHub.insights.inDays", { days }));

  return (
    <Panel title={t("subsHub.insights.title")} description={t("subsHub.insights.description")} testId="subscription-insights">
      <div className="space-y-5">
        <Section title={t("subsHub.insights.upcoming")} icon={<CalendarClock size={12} />} testId="insights-upcoming">
          {insights.upcoming.length === 0 ? (
            <p className="text-xs text-muted-foreground" data-testid="insights-upcoming-empty">{t("subsHub.insights.upcomingEmpty")}</p>
          ) : (
            <ul className="space-y-1.5">
              {insights.upcoming.slice(0, 6).map((u) => (
                <li key={u.id} className="flex items-center justify-between gap-2 rounded-lg bg-muted/40 px-3 py-1.5 text-xs" data-testid="insights-upcoming-item">
                  <span className="min-w-0 truncate">{u.name}</span>
                  <span className="shrink-0 text-muted-foreground">{dateLabel(u.date)} · {when(u.days_until)}</span>
                  <span className="shrink-0 font-mono font-semibold">{money(u.amount, u.currency, 2)}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {insights.overlaps.length > 0 && (
          <Section title={t("subsHub.insights.overlaps")} icon={<Info size={12} />} testId="insights-overlaps">
            {insights.overlaps.map((o) => (
              <p key={o.category} className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-xs text-foreground" data-testid={`insights-overlap-${o.category}`}>
                {o.message} <span className="text-muted-foreground">({t("subsHub.insights.perMonth", { amount: display(o.monthly_try) })})</span>
              </p>
            ))}
            <p className="text-[10px] text-muted-foreground">{t("subsHub.insights.overlapNote")}</p>
          </Section>
        )}

        {insights.by_category.length > 0 && (
          <Section title={t("subsHub.insights.byCategory")} icon={<Layers3 size={12} />} testId="insights-by-category">
            <ul className="space-y-1.5">
              {insights.by_category.map((b) => {
                const share = insights.monthly_total_try ? Math.round((b.monthly_try / insights.monthly_total_try) * 100) : 0;
                return (
                  <li key={b.key} className="text-xs">
                    <div className="mb-1 flex justify-between"><span>{subscriptionCategoryLabel(t, b.key)} <span className="text-muted-foreground">· {b.count}</span></span><span className="font-mono">{t("subsHub.insights.perMonth", { amount: display(b.monthly_try) })}</span></div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${share}%` }} /></div>
                  </li>
                );
              })}
            </ul>
          </Section>
        )}

        {insights.by_payment_method.length > 0 && (
          <Section title={t("subsHub.insights.byMethod")} icon={<CreditCard size={12} />} testId="insights-by-method">
            <ul className="space-y-1 text-xs">
              {insights.by_payment_method.map((b) => (
                <li key={b.key || "none"} className="flex justify-between"><span className={b.key ? "" : "text-muted-foreground"}>{b.key ? paymentMethodLabel(t, b.key) : t("subsHub.insights.noMethod")} <span className="text-muted-foreground">· {b.count}</span></span><span className="font-mono">{t("subsHub.insights.perMonth", { amount: display(b.monthly_try) })}</span></li>
              ))}
            </ul>
          </Section>
        )}

        {insights.yearly_subscriptions.length > 0 && (
          <Section title={t("subsHub.insights.yearly")} icon={<CalendarClock size={12} />} testId="insights-yearly">
            <ul className="space-y-1 text-xs">
              {insights.yearly_subscriptions.map((y) => (
                <li key={y.id} className="flex justify-between"><span>{y.name} <span className="text-muted-foreground">· {money(y.price, y.currency, 2)}</span></span><span className="font-mono">{t("subsHub.insights.perMonth", { amount: display(y.monthly_equivalent_try) })}</span></li>
              ))}
            </ul>
          </Section>
        )}

        {insights.price_changes.length > 0 && (
          <Section title={t("subsHub.insights.priceChanges")} icon={<TrendingUp size={12} />} testId="insights-price-changes">
            <ul className="space-y-1 text-xs">
              {insights.price_changes.map((p) => {
                const up = p.change_percent > 0;
                const Icon = up ? TrendingUp : TrendingDown;
                return (
                  <li key={p.id} className="flex items-center justify-between gap-2">
                    <span className="truncate">{p.name}</span>
                    <span className="flex items-center gap-1 font-mono">
                      {money(p.previous_price, p.currency, 2)} → {money(p.current_price, p.currency, 2)}
                      <Icon size={12} className={up ? "text-rose-500" : "text-emerald-500"} aria-hidden="true" />
                      <span className={up ? "text-rose-500" : "text-emerald-500"}>{up ? "+" : ""}{p.change_percent}%</span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </Section>
        )}

        {insights.legacy_unreviewed > 0 && (
          <p className="rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-xs text-amber-600 dark:text-amber-400" data-testid="insights-legacy-note">
            {t("subsHub.insights.legacyNote", { count: insights.legacy_unreviewed })}
          </p>
        )}

        {insights.active_count > 0 && <p className="text-[10px] text-muted-foreground">{t("subsHub.insights.rates")}</p>}
      </div>
    </Panel>
  );
}
