import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, PiggyBank, Sparkles } from "lucide-react";
import { apiGet } from "@/lib/api";
import { useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { SavingsReport } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EmptyState, LevelPill, PageHeader, Panel } from "@/components/shared/ui-bits";

export default function Savings() {
  const { t } = useT();
  const { data, isLoading } = useQuery({ queryKey: ["savings"], queryFn: () => apiGet<SavingsReport>("/savings"), retry: false });
  const { display } = useMoney();
  const insights = data?.insights ?? [];
  const LEVEL_LABEL = { red: t("savings.level.red"), yellow: t("savings.level.yellow"), green: t("savings.level.green") };

  return (
    <div data-testid="savings-page">
      <PageHeader eyebrow={t("savings.eyebrow")} title={t("savings.title")} description={t("savings.description")} testId="savings-header" />

      <section className="mb-6 rounded-2xl border border-primary/25 bg-gradient-to-br from-primary/15 via-card to-card p-6 sm:p-8" data-testid="savings-hero">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="flex items-center gap-2 text-sm text-muted-foreground"><PiggyBank size={16} className="text-primary" /> {t("savings.hero.label")}</p>
            <p className="mt-2 font-mono text-4xl font-bold tracking-tight sm:text-5xl" data-testid="savings-total">{display(data?.total ?? 0)}</p>
            <p className="mt-2 text-sm text-muted-foreground" data-testid="savings-summary-line">{t("savings.hero.summary", { count: insights.length, unused: data?.unused_subscriptions ?? 0 })}</p>
          </div>
          <Button render={<Link to="/assistant" />} variant="outline" data-testid="savings-ask-assistant"><Sparkles size={15} /> {t("savings.askAssistant")}</Button>
        </div>
      </section>

      <Panel title={t("savings.list.title")} description={t("savings.list.description")} testId="savings-list">
        {isLoading ? <p className="text-sm text-muted-foreground">{t("savings.loading")}</p> : insights.length === 0 ? <EmptyState title={t("savings.empty.title")} description={t("savings.empty.description")} testId="savings-empty" /> : (
          <ul className="space-y-3">
            {insights.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-background/50 p-4 transition-[border-color] hover:border-primary/40" data-testid={`insight-${i.id}`}>
                <LevelPill level={i.level} testId={`insight-level-${i.id}`}>{LEVEL_LABEL[i.level]}</LevelPill>
                <div className="min-w-[12rem] flex-1">
                  <p className="text-sm font-semibold" data-testid={`insight-title-${i.id}`}>{i.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground" data-testid={`insight-detail-${i.id}`}>{i.detail}</p>
                </div>
                <p className="font-mono text-lg font-bold text-primary" data-testid={`insight-amount-${i.id}`}>{display(i.amount)}</p>
                <Button render={<Link to={i.action_path} />} variant="ghost" size="sm" className="text-primary" data-testid={`insight-action-${i.id}`}>{i.action_label} <ArrowRight size={13} /></Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
