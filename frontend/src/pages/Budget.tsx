import { useState } from "react";
import { Plus, Target, Trash2 } from "lucide-react";
import { useCrud } from "@/hooks/useCrud";
import { EXPENSE_CATEGORIES, money, percent } from "@/lib/format";
import type { Budget, BudgetPayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityDialog, opts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, ProgressBar, StatCard } from "@/components/shared/ui-bits";
import { useSummary } from "@/pages/Dashboard";

const fields: FieldDef[] = [
  { name: "category", label: "Kategori", type: "select", options: opts(EXPENSE_CATEGORIES), full: true },
  { name: "limit", label: "Aylık limit (₺)", type: "number", required: true, full: true, hint: "Boş bırakılan ay alanı limiti her ay için geçerli yapar." },
  { name: "month", label: "Belirli bir ay (isteğe bağlı)", type: "month", full: true },
];

export default function BudgetPage() {
  const [open, setOpen] = useState(false);
  const crud = useCrud<Budget, BudgetPayload>("budgets", "/budgets");
  const summary = useSummary();
  const usage = summary.data?.budgets ?? [];
  const totalLimit = usage.reduce((s, u) => s + u.limit, 0);
  const totalSpent = usage.reduce((s, u) => s + u.spent, 0);
  const exceeded = usage.filter((u) => u.exceeded).length;

  const submit = (values: FormValues) => crud.create.mutate(values as unknown as BudgetPayload, { onSuccess: () => setOpen(false) });

  return (
    <div data-testid="budget-page">
      <PageHeader eyebrow="Bütçe" title="Aylık bütçe hedeflerin" description="Her kategori için bir üst sınır koy; Subly harcamalarını, faturalarını ve aboneliklerini bu limitlerle karşılaştırır." testId="budget-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-budget-button"><Plus size={15} /> Bütçe ekle</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="budget-stats">
        <StatCard label="Toplam limit" value={money(totalLimit)} detail={summary.data?.month_label} icon={<Target size={17} />} tone="indigo" testId="budget-total-limit" />
        <StatCard label="Kullanılan" value={money(totalSpent)} detail={totalLimit ? `Toplamın ${percent((totalSpent / totalLimit) * 100)}'i` : "Limit yok"} icon={<Target size={17} />} tone={totalSpent > totalLimit ? "rose" : "emerald"} testId="budget-total-spent" />
        <StatCard label="Aşılan kategori" value={String(exceeded)} detail={exceeded ? "Dikkat gerektiriyor" : "Her şey sınırlar içinde"} icon={<Target size={17} />} tone={exceeded ? "amber" : "cyan"} testId="budget-exceeded-count" />
      </section>

      <Panel title="Kategori bütçeleri" description="Bu ayın kullanımı" testId="budget-list">
        {usage.length === 0 ? <EmptyState title="Bütçe tanımlı değil" description="Market, ulaşım, eğlence gibi kategoriler için aylık limit belirle." action={<Button variant="outline" onClick={() => setOpen(true)} data-testid="budget-empty-add-button">İlk bütçeni oluştur</Button>} testId="budget-empty" /> : (
          <ul className="grid gap-4 md:grid-cols-2">
            {usage.map((u) => (
              <li key={u.id} className="rounded-xl border border-border bg-background/50 p-4" data-testid={`budget-card-${u.id}`}>
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold" data-testid={`budget-category-${u.id}`}>{u.category}</p>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground" data-testid={`budget-usage-${u.id}`}>{money(u.spent)} / {money(u.limit)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {u.exceeded ? <LevelPill level="red" testId={`budget-flag-${u.id}`}>⚠️ Bütçe aşıldı</LevelPill> : u.percent >= 85 ? <LevelPill level="yellow" testId={`budget-flag-${u.id}`}>Sınıra yakın</LevelPill> : <LevelPill level="green" testId={`budget-flag-${u.id}`}>{percent(u.percent)}</LevelPill>}
                    <Button variant="ghost" size="icon-xs" onClick={() => crud.remove.mutate(u.id)} className="text-muted-foreground hover:text-rose-500" aria-label="Sil" data-testid={`delete-budget-${u.id}`}><Trash2 size={13} /></Button>
                  </div>
                </div>
                <ProgressBar percent={u.percent} exceeded={u.exceeded} testId={`budget-progress-${u.id}`} />
                <p className="mt-2 text-xs text-muted-foreground">{u.exceeded ? `${money(u.spent - u.limit)} fazla harcandı` : `${money(u.limit - u.spent)} kaldı`}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <EntityDialog open={open} onClose={() => setOpen(false)} title="Yeni bütçe" description="Kategori ve aylık üst sınır." fields={fields} initial={{ category: "Market", limit: 0, month: "" }} onSubmit={submit} busy={crud.create.isPending} submitLabel="Bütçeyi oluştur" testId="budget-dialog" />
    </div>
  );
}
