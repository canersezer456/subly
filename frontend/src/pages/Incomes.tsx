import { useState } from "react";
import { Pencil, Plus, Trash2, Wallet } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { INCOME_KIND_LABELS, dateLabel, incomeKindLabel, todayIso } from "@/lib/format";
import { useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { Income, IncomePayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, translatedOpts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";

export default function Incomes() {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Income | null>(null);
  const crud = useCrud<Income, IncomePayload>("incomes", "/incomes");
  const { display } = useMoney();
  const fields: FieldDef[] = [
    { name: "source", label: t("incomes.field.source"), required: true, placeholder: t("incomes.field.sourcePlaceholder"), full: true },
    { name: "amount", label: t("incomes.field.amount"), type: "number", required: true },
    { name: "kind", label: t("incomes.field.kind"), type: "select", options: translatedOpts(Object.keys(INCOME_KIND_LABELS), (v) => incomeKindLabel(t, v)), hint: t("incomes.field.kindHint") },
    { name: "date", label: t("incomes.field.date"), type: "date", required: true, hint: t("incomes.field.dateHint") },
    { name: "note", label: t("common.note"), type: "textarea", placeholder: t("common.optional") },
  ];
  const regular = crud.items.filter((i) => i.kind === "regular").reduce((s, i) => s + i.amount, 0);
  const oneOff = crud.items.filter((i) => i.kind !== "regular").reduce((s, i) => s + i.amount, 0);

  const close = () => { setOpen(false); setEditing(null); };
  const initial: FormValues = editing ? { source: editing.source, amount: editing.amount, kind: editing.kind, date: editing.date, note: editing.note } : { source: "", amount: 0, kind: "regular", date: todayIso(), note: "" };
  const submit = (values: FormValues) => {
    const payload = values as unknown as IncomePayload;
    if (editing) crud.update.mutate({ id: editing.id, input: payload }, { onSuccess: close });
    else crud.create.mutate(payload, { onSuccess: close });
  };

  return (
    <div data-testid="incomes-page">
      <PageHeader eyebrow={t("incomes.eyebrow")} title={t("incomes.title")} description={t("incomes.description")} testId="incomes-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-income-button"><Plus size={15} /> {t("incomes.action.add")}</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="income-stats">
        <StatCard label={t("incomes.stat.regular")} value={display(regular)} detail={t("incomes.stat.regularDetail")} icon={<Wallet size={17} />} tone="emerald" testId="income-regular" />
        <StatCard label={t("incomes.stat.oneOff")} value={display(oneOff)} detail={t("incomes.stat.oneOffDetail")} icon={<Plus size={17} />} tone="cyan" testId="income-oneoff" />
        <StatCard label={t("incomes.stat.count")} value={String(crud.items.length)} detail={t("incomes.stat.countDetail")} icon={<Wallet size={17} />} tone="indigo" testId="income-count" />
      </section>

      <Panel title={t("incomes.list.title")} testId="incomes-list">
        {crud.isLoading ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="incomes-loading">{t("common.loading")}</p> : crud.items.length === 0 ? <EmptyState title={t("incomes.empty.title")} description={t("incomes.empty.description")} action={<Button variant="outline" onClick={() => setOpen(true)} data-testid="incomes-empty-add-button">{t("incomes.action.add")}</Button>} testId="incomes-empty" /> : (
          <ul className="divide-y divide-border">
            {crud.items.map((item) => (
              <li key={item.id} className="flex items-center gap-3 py-3" data-testid={`income-item-${item.id}`}>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-500/12 text-emerald-500"><Wallet size={16} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" data-testid={`income-source-${item.id}`}>{item.source}</p>
                  <p className="text-xs text-muted-foreground">{dateLabel(item.date, true)}{item.note && ` · ${item.note}`}</p>
                </div>
                <LevelPill level={item.kind === "regular" ? "green" : "info"} testId={`income-kind-${item.id}`}>{incomeKindLabel(t, item.kind)}</LevelPill>
                <p className="w-28 text-right font-mono text-sm font-semibold" data-testid={`income-amount-${item.id}`}>{display(item.amount)}</p>
                <div className="flex gap-0.5">
                  <Button variant="ghost" size="icon-sm" onClick={() => { setEditing(item); setOpen(true); }} aria-label={t("common.edit")} data-testid={`edit-income-${item.id}`}><Pencil size={14} /></Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(item.id)} className="text-muted-foreground hover:text-rose-500" aria-label={t("common.delete")} data-testid={`delete-income-${item.id}`}><Trash2 size={14} /></Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <EntityDialog open={open} onClose={close} title={editing ? t("incomes.dialog.editTitle") : t("incomes.dialog.newTitle")} fields={fields} initial={initial} onSubmit={submit} busy={crud.create.isPending || crud.update.isPending} submitLabel={editing ? t("common.save") : t("incomes.action.add")} testId="income-dialog" />
    </div>
  );
}
