import { useState } from "react";
import { Plus, Target, Trash2 } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { EXPENSE_CATEGORIES, categoryLabel, percent } from "@/lib/format";
import { useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { Budget, BudgetPayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, translatedOpts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, ProgressBar, StatCard } from "@/components/shared/ui-bits";
import { useSummary } from "@/hooks/useDashboardSummary";

export default function BudgetPage() {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const crud = useCrud<Budget, BudgetPayload>("budgets", "/budgets");
  const summary = useSummary();
  const { display } = useMoney();
  const usage = summary.data?.budgets ?? [];
  const totalLimit = usage.reduce((s, u) => s + u.limit, 0);
  const totalSpent = usage.reduce((s, u) => s + u.spent, 0);
  const exceeded = usage.filter((u) => u.exceeded).length;

  const fields: FieldDef[] = [
    { name: "category", label: t("budget.field.category"), type: "select", options: translatedOpts(EXPENSE_CATEGORIES, (v) => categoryLabel(t, v)), full: true },
    { name: "limit", label: t("budget.field.limit"), type: "number", required: true, full: true, hint: t("budget.field.limitHint") },
    { name: "month", label: t("budget.field.month"), type: "month", full: true },
  ];

  const submit = (values: FormValues) => crud.create.mutate(values as unknown as BudgetPayload, { onSuccess: () => setOpen(false) });

  return (
    <div data-testid="budget-page">
      <PageHeader eyebrow={t("budget.eyebrow")} title={t("budget.title")} description={t("budget.description")} testId="budget-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-budget-button"><Plus size={15} /> {t("budget.action.add")}</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="budget-stats">
        <StatCard label={t("budget.stat.totalLimit")} value={display(totalLimit)} detail={summary.data?.month_label} icon={<Target size={17} />} tone="indigo" testId="budget-total-limit" />
        <StatCard label={t("budget.stat.used")} value={display(totalSpent)} detail={totalLimit ? t("budget.stat.usedDetail", { percent: percent((totalSpent / totalLimit) * 100) }) : t("budget.stat.noLimit")} icon={<Target size={17} />} tone={totalSpent > totalLimit ? "rose" : "emerald"} testId="budget-total-spent" />
        <StatCard label={t("budget.stat.exceededCount")} value={String(exceeded)} detail={exceeded ? t("budget.stat.needsAttention") : t("budget.stat.allWithinLimits")} icon={<Target size={17} />} tone={exceeded ? "amber" : "cyan"} testId="budget-exceeded-count" />
      </section>

      <Panel title={t("budget.list.title")} description={t("budget.list.description")} testId="budget-list">
        {summary.isLoading ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="budget-loading">{t("common.loading")}</p> : usage.length === 0 ? <EmptyState title={t("budget.empty.title")} description={t("budget.empty.description")} action={<Button variant="outline" onClick={() => setOpen(true)} data-testid="budget-empty-add-button">{t("budget.empty.action")}</Button>} testId="budget-empty" /> : (
          <ul className="grid gap-4 md:grid-cols-2">
            {usage.map((u) => (
              <li key={u.id} className="rounded-xl border border-border bg-background/50 p-4" data-testid={`budget-card-${u.id}`}>
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold" data-testid={`budget-category-${u.id}`}>{categoryLabel(t, u.category)}</p>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground" data-testid={`budget-usage-${u.id}`}>{display(u.spent)} / {display(u.limit)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {u.exceeded ? <LevelPill level="red" testId={`budget-flag-${u.id}`}>{t("budget.flag.exceeded")}</LevelPill> : u.percent >= 85 ? <LevelPill level="yellow" testId={`budget-flag-${u.id}`}>{t("budget.flag.near")}</LevelPill> : <LevelPill level="green" testId={`budget-flag-${u.id}`}>{percent(u.percent)}</LevelPill>}
                    <Button variant="ghost" size="icon-xs" onClick={() => crud.remove.mutate(u.id)} className="text-muted-foreground hover:text-rose-500" aria-label={t("common.delete")} data-testid={`delete-budget-${u.id}`}><Trash2 size={13} /></Button>
                  </div>
                </div>
                <ProgressBar percent={u.percent} exceeded={u.exceeded} testId={`budget-progress-${u.id}`} />
                <p className="mt-2 text-xs text-muted-foreground">{u.exceeded ? t("budget.card.over", { amount: display(u.spent - u.limit) }) : t("budget.card.left", { amount: display(u.limit - u.spent) })}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <EntityDialog open={open} onClose={() => setOpen(false)} title={t("budget.dialog.title")} description={t("budget.dialog.description")} fields={fields} initial={{ category: "Market", limit: 0, month: "" }} onSubmit={submit} busy={crud.create.isPending} submitLabel={t("budget.dialog.submit")} testId="budget-dialog" />
    </div>
  );
}
