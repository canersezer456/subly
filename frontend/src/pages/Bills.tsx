import { useState } from "react";
import { CheckCircle2, Pencil, Plus, Receipt, RotateCcw, Trash2, Zap } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { BILL_TYPES, BILL_TYPE_ICONS, FREQUENCY_LABELS, PAYMENT_METHODS, billTypeLabel, dateLabel, frequencyLabel, paymentMethodLabel, todayIso } from "@/lib/format";
import { useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { Bill, BillPayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, translatedOpts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";

export default function Bills() {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Bill | null>(null);
  const crud = useCrud<Bill, BillPayload>("bills", "/bills");
  const { display } = useMoney();
  const fields: FieldDef[] = [
    { name: "provider", label: t("bills.field.provider"), required: true, placeholder: t("bills.field.providerPlaceholder"), full: true },
    { name: "bill_type", label: t("bills.field.type"), type: "select", options: translatedOpts(BILL_TYPES, (v) => billTypeLabel(t, v)) },
    { name: "amount", label: t("bills.field.amount"), type: "number", required: true },
    { name: "due_date", label: t("bills.field.dueDate"), type: "date", required: true },
    { name: "frequency", label: t("bills.field.frequency"), type: "select", options: translatedOpts(Object.keys(FREQUENCY_LABELS), (v) => frequencyLabel(t, v)) },
    { name: "payment_method", label: t("bills.field.paymentMethod"), type: "select", options: translatedOpts(PAYMENT_METHODS, (v) => paymentMethodLabel(t, v)) },
    { name: "bill_number", label: t("bills.field.billNumber"), placeholder: t("common.optional") },
    { name: "auto_pay", label: t("bills.field.autoPay"), type: "checkbox", full: true },
    { name: "note", label: t("common.note"), type: "textarea", placeholder: t("common.optional") },
  ];
  const pending = crud.items.filter((b) => b.status === "pending");
  const pendingTotal = pending.reduce((s, b) => s + b.amount, 0);
  const autoPay = crud.items.filter((b) => b.auto_pay && b.status === "pending").length;

  const close = () => { setOpen(false); setEditing(null); };
  const initial: FormValues = editing
    ? { provider: editing.provider, bill_type: editing.bill_type, amount: editing.amount, due_date: editing.due_date, frequency: editing.frequency, payment_method: editing.payment_method, bill_number: editing.bill_number, auto_pay: editing.auto_pay, note: editing.note }
    : { provider: "", bill_type: "Elektrik", amount: 0, due_date: todayIso(), frequency: "monthly", payment_method: "Havale / EFT", bill_number: "", auto_pay: false, note: "" };
  const submit = (values: FormValues) => {
    const payload = values as unknown as BillPayload;
    if (editing) crud.update.mutate({ id: editing.id, input: payload }, { onSuccess: close });
    else crud.create.mutate(payload, { onSuccess: close });
  };

  return (
    <div data-testid="bills-page">
      <PageHeader eyebrow={t("bills.eyebrow")} title={t("bills.title")} description={t("bills.description")} testId="bills-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-bill-button"><Plus size={15} /> {t("bills.action.add")}</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="bill-stats">
        <StatCard label={t("bills.stat.pendingTotal")} value={display(pendingTotal)} detail={t("bills.stat.pendingDetail", { count: pending.length })} icon={<Receipt size={17} />} tone="amber" testId="bills-pending-total" />
        <StatCard label={t("bills.stat.autoPay")} value={String(autoPay)} detail={t("bills.stat.autoPayDetail")} icon={<Zap size={17} />} tone="cyan" testId="bills-autopay-count" />
        <StatCard label={t("bills.stat.total")} value={String(crud.items.length)} detail={t("bills.stat.totalDetail")} icon={<CheckCircle2 size={17} />} tone="emerald" testId="bills-count" />
      </section>

      <Panel title={t("bills.list.title")} description={t("bills.list.description")} testId="bills-list">
        {crud.isLoading ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="bills-loading">{t("common.loading")}</p> : crud.items.length === 0 ? <EmptyState title={t("bills.empty.title")} description={t("bills.empty.description")} action={<Button variant="outline" onClick={() => setOpen(true)} data-testid="bills-empty-add-button">{t("bills.action.add")}</Button>} testId="bills-empty" /> : (
          <ul className="divide-y divide-border">
            {crud.items.map((bill) => (
              <li key={bill.id} className="flex flex-wrap items-center gap-3 py-3" data-testid={`bill-item-${bill.id}`}>
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-muted text-lg" aria-hidden>{BILL_TYPE_ICONS[bill.bill_type] ?? "📋"}</span>
                <div className="min-w-[10rem] flex-1">
                  <p className="text-sm font-medium" data-testid={`bill-provider-${bill.id}`}>{bill.provider}</p>
                  <p className="text-xs text-muted-foreground">{billTypeLabel(t, bill.bill_type)} · {frequencyLabel(t, bill.frequency)} · {t("bills.item.due")} {dateLabel(bill.due_date, true)}{bill.bill_number && ` · #${bill.bill_number}`}</p>
                </div>
                <div className="flex items-center gap-2">
                  {bill.auto_pay && <LevelPill level="info">{t("bills.item.auto")}</LevelPill>}
                  <LevelPill level={bill.status === "paid" ? "green" : "yellow"} testId={`bill-status-${bill.id}`}>{bill.status === "paid" ? t("bills.status.paid") : t("bills.status.pending")}</LevelPill>
                </div>
                <p className="w-24 text-right font-mono text-sm font-semibold" data-testid={`bill-amount-${bill.id}`}>{display(bill.amount)}</p>
                <div className="flex gap-0.5">
                  {bill.status === "pending"
                    ? <Button variant="outline" size="sm" onClick={() => crud.update.mutate({ id: bill.id, input: { status: "paid" } })} data-testid={`mark-paid-${bill.id}`}><CheckCircle2 size={13} /> {t("bills.action.markPaid")}</Button>
                    : <Button variant="ghost" size="sm" onClick={() => crud.update.mutate({ id: bill.id, input: { status: "pending" } })} className="text-muted-foreground" data-testid={`mark-pending-${bill.id}`}><RotateCcw size={13} /> {t("bills.action.markPending")}</Button>}
                  <Button variant="ghost" size="icon-sm" onClick={() => { setEditing(bill); setOpen(true); }} aria-label={t("common.edit")} data-testid={`edit-bill-${bill.id}`}><Pencil size={14} /></Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(bill.id)} className="text-muted-foreground hover:text-rose-500" aria-label={t("common.delete")} data-testid={`delete-bill-${bill.id}`}><Trash2 size={14} /></Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <p className="mt-4 text-xs text-muted-foreground" data-testid="bills-ocr-note">{t("bills.ocrNote")}</p>

      <EntityDialog open={open} onClose={close} title={editing ? t("bills.dialog.editTitle") : t("bills.dialog.newTitle")} fields={fields} initial={initial} onSubmit={submit} busy={crud.create.isPending || crud.update.isPending} submitLabel={editing ? t("common.save") : t("bills.action.add")} testId="bill-dialog" />
    </div>
  );
}
