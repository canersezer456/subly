import { useState } from "react";
import { Pencil, Plus, Trash2, Wallet } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { INCOME_KIND_LABELS, dateLabel, money, todayIso } from "@/lib/format";
import type { Income, IncomePayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, labelled, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";

const fields: FieldDef[] = [
  { name: "source", label: "Gelir kaynağı", required: true, placeholder: "Örn. Maaş", full: true },
  { name: "amount", label: "Tutar (₺)", type: "number", required: true },
  { name: "kind", label: "Tür", type: "select", options: labelled(INCOME_KIND_LABELS), hint: "Düzenli gelir her ay otomatik sayılır." },
  { name: "date", label: "Tarih", type: "date", required: true, hint: "Düzenli gelir için ilk ödeme günü." },
  { name: "note", label: "Not", type: "textarea", placeholder: "İsteğe bağlı" },
];

export default function Incomes() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Income | null>(null);
  const crud = useCrud<Income, IncomePayload>("incomes", "/incomes");
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
      <PageHeader eyebrow="Gelirler" title="Gelir kaynakların" description="Maaş, freelance ve ek gelirlerini ayır; düzenli olanlar her ayın bütçesine otomatik girer." testId="incomes-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-income-button"><Plus size={15} /> Gelir ekle</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="income-stats">
        <StatCard label="Düzenli aylık gelir" value={money(regular)} detail="Her ay tekrar eder" icon={<Wallet size={17} />} tone="emerald" testId="income-regular" />
        <StatCard label="Tek seferlik + ek" value={money(oneOff)} detail="Kayıtlı tüm dönemler" icon={<Plus size={17} />} tone="cyan" testId="income-oneoff" />
        <StatCard label="Kaynak sayısı" value={String(crud.items.length)} detail="Aktif gelir kalemi" icon={<Wallet size={17} />} tone="indigo" testId="income-count" />
      </section>

      <Panel title="Gelir kalemleri" testId="incomes-list">
        {crud.items.length === 0 ? <EmptyState title="Henüz gelir eklenmedi" description="Maaşını ekleyerek başla; kalan ve tasarruf oranın hesaplanır." action={<Button variant="outline" onClick={() => setOpen(true)} data-testid="incomes-empty-add-button">Gelir ekle</Button>} testId="incomes-empty" /> : (
          <ul className="divide-y divide-border">
            {crud.items.map((item) => (
              <li key={item.id} className="flex items-center gap-3 py-3" data-testid={`income-item-${item.id}`}>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-500/12 text-emerald-500"><Wallet size={16} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" data-testid={`income-source-${item.id}`}>{item.source}</p>
                  <p className="text-xs text-muted-foreground">{dateLabel(item.date, true)}{item.note && ` · ${item.note}`}</p>
                </div>
                <LevelPill level={item.kind === "regular" ? "green" : "info"} testId={`income-kind-${item.id}`}>{INCOME_KIND_LABELS[item.kind]}</LevelPill>
                <p className="w-28 text-right font-mono text-sm font-semibold" data-testid={`income-amount-${item.id}`}>{money(item.amount)}</p>
                <div className="flex gap-0.5">
                  <Button variant="ghost" size="icon-sm" onClick={() => { setEditing(item); setOpen(true); }} aria-label="Düzenle" data-testid={`edit-income-${item.id}`}><Pencil size={14} /></Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(item.id)} className="text-muted-foreground hover:text-rose-500" aria-label="Sil" data-testid={`delete-income-${item.id}`}><Trash2 size={14} /></Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <EntityDialog open={open} onClose={close} title={editing ? "Geliri düzenle" : "Yeni gelir"} fields={fields} initial={initial} onSubmit={submit} busy={crud.create.isPending || crud.update.isPending} submitLabel={editing ? "Kaydet" : "Geliri ekle"} testId="income-dialog" />
    </div>
  );
}
