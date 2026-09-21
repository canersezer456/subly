import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { EXPENSE_CATEGORIES, PAYMENT_METHODS, dateLabel, money, monthIso, todayIso } from "@/lib/format";
import type { Expense, ExpensePayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, opts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, PageHeader, Panel } from "@/components/shared/ui-bits";

const fields: FieldDef[] = [
  { name: "title", label: "Açıklama", required: true, placeholder: "Örn. Haftalık market", full: true },
  { name: "amount", label: "Tutar (₺)", type: "number", required: true },
  { name: "category", label: "Kategori", type: "select", options: opts(EXPENSE_CATEGORIES) },
  { name: "date", label: "Tarih", type: "date", required: true },
  { name: "payment_method", label: "Ödeme yöntemi", type: "select", options: opts(PAYMENT_METHODS) },
  { name: "note", label: "Not", type: "textarea", placeholder: "İsteğe bağlı" },
];

export default function Expenses() {
  const [params, setParams] = useSearchParams();
  const [month, setMonth] = useState(monthIso());
  const [editing, setEditing] = useState<Expense | null>(null);
  const open = params.get("new") === "1" || editing !== null;
  const crud = useCrud<Expense, ExpensePayload>("expenses", "/expenses", `?month=${month}`);

  const total = crud.items.reduce((sum, item) => sum + item.amount, 0);
  const byCategory = useMemo(() => {
    const map = new Map<string, number>();
    crud.items.forEach((item) => map.set(item.category, (map.get(item.category) ?? 0) + item.amount));
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [crud.items]);

  const close = () => { setEditing(null); if (params.has("new")) { params.delete("new"); setParams(params, { replace: true }); } };
  const initial: FormValues = editing ? { title: editing.title, amount: editing.amount, category: editing.category, date: editing.date, payment_method: editing.payment_method, note: editing.note } : { title: "", amount: 0, category: "Market", date: todayIso(), payment_method: PAYMENT_METHODS[0], note: "" };
  const submit = (values: FormValues) => {
    const payload = values as unknown as ExpensePayload;
    const done = { onSuccess: close };
    if (editing) crud.update.mutate({ id: editing.id, input: payload }, done);
    else crud.create.mutate(payload, done);
  };

  return (
    <div data-testid="expenses-page">
      <PageHeader eyebrow="Harcamalar" title="Param nereye gidiyor?" description="Manuel girdiğin harcamalar; faturalar ve abonelikler ayrıca otomatik dahil edilir, onları burada tekrar ekleme." testId="expenses-header"
        actions={<>
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="h-9 rounded-lg border border-input bg-card px-3 text-sm" data-testid="expenses-month-filter" />
          <Button onClick={() => setParams({ new: "1" })} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-expense-button"><Plus size={15} /> Harcama ekle</Button>
        </>} />

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Panel title="Harcama listesi" description={`${crud.items.length} kayıt · toplam ${money(total)}`} testId="expenses-list">
          {crud.items.length === 0 ? <EmptyState title="Bu ay harcama yok" description="İlk harcamanı ekle; kategori dağılımı ve bütçe takibi otomatik güncellenir." action={<Button variant="outline" onClick={() => setParams({ new: "1" })} data-testid="expenses-empty-add-button">Harcama ekle</Button>} testId="expenses-empty" /> : (
            <ul className="divide-y divide-border">
              {crud.items.map((item) => (
                <li key={item.id} className="flex items-center gap-3 py-3" data-testid={`expense-item-${item.id}`}>
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-muted font-mono text-[10px] text-muted-foreground">{item.category.slice(0, 3).toUpperCase()}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium" data-testid={`expense-title-${item.id}`}>{item.title}</p>
                    <p className="text-xs text-muted-foreground">{item.category} · {dateLabel(item.date)} · {item.payment_method}</p>
                  </div>
                  <p className="font-mono text-sm font-semibold" data-testid={`expense-amount-${item.id}`}>{money(item.amount, "TRY", 2)}</p>
                  <div className="flex gap-0.5">
                    <Button variant="ghost" size="icon-sm" onClick={() => setEditing(item)} aria-label="Düzenle" data-testid={`edit-expense-${item.id}`}><Pencil size={14} /></Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(item.id)} className="text-muted-foreground hover:text-rose-500" aria-label="Sil" data-testid={`delete-expense-${item.id}`}><Trash2 size={14} /></Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Kategori özeti" description="Seçili ay" testId="expenses-category-summary">
          {byCategory.length === 0 ? <p className="text-sm text-muted-foreground">Veri yok.</p> : (
            <ul className="space-y-2.5">
              {byCategory.map(([category, amount]) => (
                <li key={category} className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm" data-testid={`expense-category-${category}`}>
                  <span>{category}</span><span className="font-mono">{money(amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <EntityDialog open={open} onClose={close} title={editing ? "Harcamayı düzenle" : "Yeni harcama"} description="Tutarı ve kategoriyi gir; bütçe kullanımın anında güncellenir." fields={fields} initial={initial} onSubmit={submit} busy={crud.create.isPending || crud.update.isPending} submitLabel={editing ? "Kaydet" : "Harcamayı ekle"} testId="expense-dialog" />
    </div>
  );
}
