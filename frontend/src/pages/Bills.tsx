import { useState } from "react";
import { CheckCircle2, Pencil, Plus, Receipt, RotateCcw, Trash2, Zap } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { BILL_TYPES, BILL_TYPE_ICONS, FREQUENCY_LABELS, PAYMENT_METHODS, dateLabel, money, todayIso } from "@/lib/format";
import type { Bill, BillPayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, labelled, opts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";

const fields: FieldDef[] = [
  { name: "provider", label: "Kurum", required: true, placeholder: "Örn. CK Boğaziçi Elektrik", full: true },
  { name: "bill_type", label: "Fatura türü", type: "select", options: opts(BILL_TYPES) },
  { name: "amount", label: "Tutar (₺)", type: "number", required: true },
  { name: "due_date", label: "Son ödeme tarihi", type: "date", required: true },
  { name: "frequency", label: "Tekrarlama", type: "select", options: labelled(FREQUENCY_LABELS) },
  { name: "payment_method", label: "Ödeme yöntemi", type: "select", options: opts(PAYMENT_METHODS) },
  { name: "bill_number", label: "Fatura numarası", placeholder: "İsteğe bağlı" },
  { name: "auto_pay", label: "Otomatik ödeme talimatı var", type: "checkbox", full: true },
  { name: "note", label: "Not", type: "textarea", placeholder: "İsteğe bağlı" },
];

export default function Bills() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Bill | null>(null);
  const crud = useCrud<Bill, BillPayload>("bills", "/bills");
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
      <PageHeader eyebrow="Faturalar" title="Düzenli faturaların" description="Elektrik, su, kira gibi sabit ödemelerini takip et. Ödediğinde işaretle; tekrar eden faturalar bir sonraki döneme otomatik taşınır." testId="bills-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-bill-button"><Plus size={15} /> Fatura ekle</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="bill-stats">
        <StatCard label="Bekleyen toplam" value={money(pendingTotal)} detail={`${pending.length} ödenmemiş fatura`} icon={<Receipt size={17} />} tone="amber" testId="bills-pending-total" />
        <StatCard label="Otomatik ödeme" value={String(autoPay)} detail="Talimatlı fatura" icon={<Zap size={17} />} tone="cyan" testId="bills-autopay-count" />
        <StatCard label="Toplam kayıt" value={String(crud.items.length)} detail="Aktif ve geçmiş" icon={<CheckCircle2 size={17} />} tone="emerald" testId="bills-count" />
      </section>

      <Panel title="Fatura listesi" description="Son ödeme tarihine göre sıralı" testId="bills-list">
        {crud.items.length === 0 ? <EmptyState title="Fatura yok" description="İlk faturanı ekle; takvimde ve yaklaşan ödemelerde görünmeye başlar." action={<Button variant="outline" onClick={() => setOpen(true)} data-testid="bills-empty-add-button">Fatura ekle</Button>} testId="bills-empty" /> : (
          <ul className="divide-y divide-border">
            {crud.items.map((bill) => (
              <li key={bill.id} className="flex flex-wrap items-center gap-3 py-3" data-testid={`bill-item-${bill.id}`}>
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-muted text-lg" aria-hidden>{BILL_TYPE_ICONS[bill.bill_type] ?? "📋"}</span>
                <div className="min-w-[10rem] flex-1">
                  <p className="text-sm font-medium" data-testid={`bill-provider-${bill.id}`}>{bill.provider}</p>
                  <p className="text-xs text-muted-foreground">{bill.bill_type} · {FREQUENCY_LABELS[bill.frequency]} · Son ödeme {dateLabel(bill.due_date, true)}{bill.bill_number && ` · #${bill.bill_number}`}</p>
                </div>
                <div className="flex items-center gap-2">
                  {bill.auto_pay && <LevelPill level="info">Otomatik</LevelPill>}
                  <LevelPill level={bill.status === "paid" ? "green" : "yellow"} testId={`bill-status-${bill.id}`}>{bill.status === "paid" ? "Ödendi" : "Bekliyor"}</LevelPill>
                </div>
                <p className="w-24 text-right font-mono text-sm font-semibold" data-testid={`bill-amount-${bill.id}`}>{money(bill.amount)}</p>
                <div className="flex gap-0.5">
                  {bill.status === "pending"
                    ? <Button variant="outline" size="sm" onClick={() => crud.update.mutate({ id: bill.id, input: { status: "paid" } })} data-testid={`mark-paid-${bill.id}`}><CheckCircle2 size={13} /> Ödendi</Button>
                    : <Button variant="ghost" size="sm" onClick={() => crud.update.mutate({ id: bill.id, input: { status: "pending" } })} className="text-muted-foreground" data-testid={`mark-pending-${bill.id}`}><RotateCcw size={13} /> Geri al</Button>}
                  <Button variant="ghost" size="icon-sm" onClick={() => { setEditing(bill); setOpen(true); }} aria-label="Düzenle" data-testid={`edit-bill-${bill.id}`}><Pencil size={14} /></Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(bill.id)} className="text-muted-foreground hover:text-rose-500" aria-label="Sil" data-testid={`delete-bill-${bill.id}`}><Trash2 size={14} /></Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <p className="mt-4 text-xs text-muted-foreground" data-testid="bills-ocr-note">PDF / fotoğraf yükleme ve OCR ile otomatik okuma bir sonraki sürümde eklenecek.</p>

      <EntityDialog open={open} onClose={close} title={editing ? "Faturayı düzenle" : "Yeni fatura"} fields={fields} initial={initial} onSubmit={submit} busy={crud.create.isPending || crud.update.isPending} submitLabel={editing ? "Kaydet" : "Faturayı ekle"} testId="bill-dialog" />
    </div>
  );
}
