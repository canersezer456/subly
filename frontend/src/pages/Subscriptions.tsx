import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowUpRight, CreditCard, Database, ExternalLink, Gift, Pencil, Plus, RefreshCw, Search, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { useCrud } from "@/hooks/useCrud";
import { PAYMENT_METHODS, SUBSCRIPTION_CATEGORIES, USAGE_LABELS, dateLabel, money, paymentMethodLabel, subscriptionCategoryLabel, todayIso, usageLabel } from "@/lib/format";
import { toTry, useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { Deal, MockScanResponse, Subscription, SubscriptionPayload } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProviderMark } from "@/components/brand/ProviderMark";
import { InstallPrompt } from "@/components/mobile/InstallPrompt";
import { EntityDialog, opts, translatedOpts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";
import { cn } from "@/lib/utils";

const monthlyTry = (s: Subscription) => toTry(s.price, s.currency) / (s.billing_cycle === "yearly" ? 12 : 1);
const ALL_CATEGORIES = "__all__";

function MockBadge({ t }: { t: (key: string) => string }) { return <Badge className="border border-violet-400/30 bg-violet-400/10 text-violet-400" data-testid="mocked-data-indicator">{t("subscriptions.mockedBadge")}</Badge>; }

export default function Subscriptions() {
  const { t } = useT();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "list";
  const setTab = (next: string) => setParams(next === "list" ? {} : { tab: next }, { replace: true });
  const queryClient = useQueryClient();
  const crud = useCrud<Subscription, SubscriptionPayload>("subscriptions", "/subscriptions");
  const { display } = useMoney();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Subscription | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const [scan, setScan] = useState<MockScanResponse | null>(null);

  const fields: FieldDef[] = [
    { name: "name", label: t("subscriptions.field.name"), required: true, placeholder: t("subscriptions.field.namePlaceholder"), full: true },
    { name: "category", label: t("subscriptions.field.category"), type: "select", options: translatedOpts(SUBSCRIPTION_CATEGORIES, (v) => subscriptionCategoryLabel(t, v)) },
    { name: "price", label: t("subscriptions.field.price"), type: "number", required: true },
    { name: "currency", label: t("subscriptions.field.currency"), type: "select", options: opts(["TRY", "USD", "EUR"]) },
    { name: "billing_cycle", label: t("subscriptions.field.billingCycle"), type: "select", options: [{ value: "monthly", label: t("subscriptions.cycle.monthly") }, { value: "yearly", label: t("subscriptions.cycle.yearly") }] },
    { name: "renewal_date", label: t("subscriptions.field.renewalDate"), type: "date", required: true },
    { name: "payment_method", label: t("subscriptions.field.paymentMethod"), type: "select", options: translatedOpts(PAYMENT_METHODS, (v) => paymentMethodLabel(t, v)) },
    { name: "usage", label: t("subscriptions.field.usage"), type: "select", options: translatedOpts(Object.keys(USAGE_LABELS), (v) => usageLabel(t, v)), hint: t("subscriptions.field.usageHint") },
    { name: "cancellation_url", label: t("subscriptions.field.cancellationUrl"), type: "url", full: true },
  ];

  const deals = useQuery({ queryKey: ["deals"], queryFn: () => apiGet<Deal[]>("/subscriptions/deals"), enabled: tab === "deals", retry: false });
  const scanMutation = useMutation({ mutationFn: () => apiPost<MockScanResponse>("/subscriptions/mock-scan"), onSuccess: (r) => { setScan(r); toast.success(t("subscriptions.scan.done")); } });

  const active = crud.items.filter((s) => s.status !== "cancelled");
  const monthly = active.reduce((sum, s) => sum + monthlyTry(s), 0);
  const filtered = useMemo(() => crud.items.filter((s) => (category === ALL_CATEGORIES || s.category === category) && s.name.toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))), [crud.items, category, search]);
  const byMethod = useMemo(() => {
    const map = new Map<string, Subscription[]>();
    active.forEach((s) => map.set(s.payment_method, [...(map.get(s.payment_method) ?? []), s]));
    return [...map.entries()];
  }, [active]);

  const close = () => { setOpen(false); setEditing(null); };
  const initial: FormValues = editing
    ? { name: editing.name, category: editing.category, price: editing.price, currency: editing.currency, billing_cycle: editing.billing_cycle, renewal_date: editing.renewal_date, payment_method: editing.payment_method, usage: editing.usage, cancellation_url: editing.cancellation_url }
    : { name: "", category: "Eğlence", price: 0, currency: "TRY", billing_cycle: "monthly", renewal_date: todayIso(), payment_method: PAYMENT_METHODS[0], usage: "active", cancellation_url: "https://www.google.com" };
  const submit = (values: FormValues) => {
    const payload = values as unknown as SubscriptionPayload;
    if (editing) crud.update.mutate({ id: editing.id, input: payload }, { onSuccess: close });
    else crud.create.mutate(payload, { onSuccess: close });
  };
  const cancel = (sub: Subscription) => {
    window.open(sub.cancellation_url, "_blank", "noopener,noreferrer");
    crud.update.mutate({ id: sub.id, input: { status: "cancelled" } });
  };
  const addDetected = (item: SubscriptionPayload) => crud.create.mutate(item, { onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subscriptions"] }) });

  const tabs = [{ id: "list", label: t("subscriptions.tab.list"), icon: RefreshCw }, { id: "scan", label: t("subscriptions.tab.scan"), icon: Database }, { id: "deals", label: t("subscriptions.tab.deals"), icon: Gift }];

  return (
    <div data-testid="subscriptions-page">
      <PageHeader eyebrow={t("subscriptions.eyebrow")} title={t("subscriptions.title")} description={t("subscriptions.description")} testId="subscriptions-header"
        actions={<Button onClick={() => setOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-subscription-button"><Plus size={15} /> {t("subscriptions.action.add")}</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="subscription-stats">
        <StatCard label={t("subscriptions.stat.monthly")} value={display(monthly)} detail={t("subscriptions.stat.monthlyDetail", { count: active.length })} icon={<RefreshCw size={17} />} tone="emerald" testId="subs-monthly" />
        <StatCard label={t("subscriptions.stat.yearly")} value={display(monthly * 12)} detail={t("subscriptions.stat.yearlyDetail")} icon={<CreditCard size={17} />} tone="indigo" testId="subs-yearly" />
        <StatCard label={t("subscriptions.stat.unused")} value={String(active.filter((s) => s.usage === "unused").length)} detail={t("subscriptions.stat.unusedDetail", { count: active.filter((s) => s.usage === "rarely").length })} icon={<Sparkles size={17} />} tone="amber" to="/savings" testId="subs-unused" />
      </section>

      <div className="mb-5 flex gap-1 rounded-xl border border-border bg-card p-1 sm:w-fit" data-testid="subscription-tabs">
        {tabs.map((tabItem) => { const Icon = tabItem.icon; return <button key={tabItem.id} type="button" onClick={() => setTab(tabItem.id)} className={cn("flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs transition-colors sm:flex-none", tab === tabItem.id ? "bg-primary/12 font-medium text-primary" : "text-muted-foreground hover:text-foreground")} data-testid={`nav-${tabItem.id}-tab`}><Icon size={14} />{tabItem.label}</button>; })}
      </div>

      {tab === "list" && (
        <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
          <Panel testId="subscription-list" title={t("subscriptions.list.title")} description={t("subscriptions.list.description", { count: filtered.length })}
            action={<div className="flex gap-2">
              <div className="relative"><Search size={14} className="absolute left-2.5 top-2.5 text-muted-foreground" /><Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("subscriptions.search")} className="h-9 w-36 pl-8 text-sm" data-testid="subscription-search-input" /></div>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="h-9 rounded-lg border border-input bg-background px-2 text-sm" data-testid="filter-category-select"><option value={ALL_CATEGORIES}>{t("common.all")}</option>{SUBSCRIPTION_CATEGORIES.map((c) => <option key={c} value={c}>{subscriptionCategoryLabel(t, c)}</option>)}</select>
            </div>}>
            {crud.isLoading ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="subscriptions-loading">{t("common.loading")}</p> : filtered.length === 0 ? <EmptyState title={t("subscriptions.empty.title")} description={t("subscriptions.empty.description")} testId="subscription-empty-state" /> : (
              <ul className="divide-y divide-border">
                {filtered.map((sub) => (
                  <li key={sub.id} className="flex flex-wrap items-center gap-3 py-3.5" data-testid="subscription-item">
                    <ProviderMark name={sub.name} />
                    <div className="min-w-[9rem] flex-1">
                      <p className="text-sm font-medium" data-testid="subscription-name">{sub.name}</p>
                      <p className="text-xs text-muted-foreground">{subscriptionCategoryLabel(t, sub.category)} · {paymentMethodLabel(t, sub.payment_method)} · {t("subscriptions.item.renewal")} {dateLabel(sub.renewal_date)}</p>
                    </div>
                    <LevelPill level={sub.usage === "unused" ? "red" : sub.usage === "rarely" ? "yellow" : "green"} testId="subscription-usage-badge">{usageLabel(t, sub.usage)}</LevelPill>
                    <div className="w-28 text-right">
                      <p className="font-mono text-sm font-semibold" data-testid="subscription-price">{money(sub.price, sub.currency, 2)}</p>
                      <p className="text-[11px] text-muted-foreground">{sub.billing_cycle === "yearly" ? t("subscriptions.cycle.yearly") : t("subscriptions.cycle.monthly")}{sub.status === "cancelled" && <span className="ml-1 text-rose-500" data-testid="subscription-status-badge">· {t("subscriptions.item.cancelled")}</span>}</p>
                    </div>
                    <div className="flex gap-0.5">
                      <Button variant="ghost" size="icon-sm" onClick={() => { setEditing(sub); setOpen(true); }} aria-label={t("common.edit")} data-testid="edit-subscription-button"><Pencil size={14} /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => cancel(sub)} disabled={sub.status === "cancelled"} className="text-rose-500" aria-label={t("subscriptions.item.oneClickCancel")} title={t("subscriptions.item.openCancelPage")} data-testid="one-click-cancel-button"><ExternalLink size={14} /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(sub.id)} className="text-muted-foreground hover:text-rose-500" aria-label={t("common.delete")} data-testid="delete-subscription-button"><Trash2 size={14} /></Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("subscriptions.byMethod.title")} description={t("subscriptions.byMethod.description")} testId="subscriptions-by-method">
            {byMethod.length === 0 ? <p className="text-sm text-muted-foreground">{t("subscriptions.byMethod.empty")}</p> : (
              <div className="space-y-4">
                {byMethod.map(([method, subs]) => (
                  <div key={method} className="rounded-xl border border-border p-3" data-testid={`method-group-${method}`}>
                    <div className="mb-2 flex items-center justify-between text-sm"><span className="flex items-center gap-2 font-medium"><CreditCard size={14} className="text-muted-foreground" />{paymentMethodLabel(t, method)}</span><span className="font-mono text-xs text-muted-foreground">{t("subscriptions.byMethod.perMonth", { amount: display(subs.reduce((s, x) => s + monthlyTry(x), 0)) })}</span></div>
                    <ul className="space-y-1 text-xs text-muted-foreground">{subs.map((s) => <li key={s.id} className="flex justify-between"><span>{s.name}</span><span className="font-mono">{money(s.price, s.currency, 2)}</span></li>)}</ul>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      )}

      {tab === "scan" && (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.3fr]">
          <Panel testId="scan-panel" className="border-violet-400/25">
            <MockBadge t={t} />
            <p className="mt-4 font-heading text-xl font-bold" data-testid="scan-panel-title">{t("subscriptions.scan.title")}</p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground" data-testid="scan-panel-description">{t("subscriptions.scan.description")}</p>
            <div className="my-6 rounded-xl border border-border bg-background/60 p-4" data-testid="mocked-data-indicator-banner">
              <div className="mb-3 flex justify-between text-xs text-muted-foreground"><span>{t("subscriptions.scan.engine")}</span><span className="text-violet-400">{scanMutation.isPending ? t("subscriptions.scan.analyzing") : t("subscriptions.scan.ready")}</span></div>
              <div className="h-2 overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full bg-violet-400", scanMutation.isPending ? "w-2/3 animate-pulse" : "w-1/4")} /></div>
            </div>
            <Button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending} className="w-full bg-violet-500 text-white hover:bg-violet-400" data-testid="trigger-mock-bank-scan-button">{scanMutation.isPending ? t("subscriptions.scan.scanning") : t("subscriptions.scan.start")}</Button>
            <p className="mt-4 text-xs text-muted-foreground" data-testid="scan-privacy-note"><ShieldCheck size={12} className="mr-1 inline text-primary" />{t("subscriptions.scan.privacy")}</p>
          </Panel>
          <Panel title={t("subscriptions.scan.resultsTitle")} description={scan ? t("subscriptions.scan.resultsFound", { count: scan.detected.length }) : t("subscriptions.scan.resultsEmpty")} testId="scan-results-card" action={scan && <MockBadge t={t} />}>
            {scan ? (
              <ul className="space-y-3">
                {scan.detected.map((item) => (
                  <li key={item.name} className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="detected-subscription-item">
                    <ProviderMark name={item.name} size="sm" />
                    <div className="flex-1"><p className="text-sm font-medium" data-testid="detected-subscription-name">{item.name}</p><p className="text-xs text-muted-foreground">{subscriptionCategoryLabel(t, item.category)} · {money(item.price, item.currency, 2)} / {t("subscriptions.perMonthShort")}</p></div>
                    <Button size="sm" onClick={() => addDetected(item)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-detected-subscription-button"><Plus size={13} /> {t("subscriptions.scan.addToList")}</Button>
                  </li>
                ))}
              </ul>
            ) : <EmptyState title={t("subscriptions.scan.emptyTitle")} description={t("subscriptions.scan.emptyDescription")} testId="scan-empty-state" />}
          </Panel>
        </div>
      )}

      {tab === "deals" && <DealsPanel deals={deals.data ?? []} t={t} />}

      <EntityDialog open={open} onClose={close} title={editing ? t("subscriptions.dialog.editTitle") : t("subscriptions.dialog.newTitle")} fields={fields} initial={initial} onSubmit={submit} busy={crud.create.isPending || crud.update.isPending} submitLabel={editing ? t("common.save") : t("subscriptions.action.add")} testId="subscription-dialog" />
    </div>
  );
}

function DealsPanel({ deals, t }: { deals: Deal[]; t: (key: string, vars?: Record<string, string | number>) => string }) {
  return (
    <div className="space-y-5" data-testid="deals-panel">
      <div className="rounded-2xl border border-amber-400/25 bg-gradient-to-br from-amber-400/15 via-card to-card p-6" data-testid="deals-hero">
        <div className="flex flex-wrap items-center gap-2"><Badge className="border border-amber-400/30 bg-amber-400/15 text-amber-500"><Gift size={13} className="mr-1" />{t("subscriptions.deals.badge")}</Badge><Badge variant="outline" data-testid="deals-example-label">{t("subscriptions.deals.exampleLabel")}</Badge></div>
        <h2 className="mt-3 font-heading text-2xl font-bold" data-testid="deals-hero-title">{t("subscriptions.deals.title")}</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground" data-testid="deals-hero-description">{t("subscriptions.deals.description")}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {deals.map((deal) => (
          <Panel key={deal.id} testId="deal-card" className="transition-[border-color,transform] hover:-translate-y-0.5 hover:border-primary/40">
            <div className="mb-4 flex items-start justify-between"><ProviderMark name={deal.provider} /><span className="rounded-full bg-primary px-2.5 py-1 font-mono text-xs font-bold text-primary-foreground" data-testid="deal-discount">%{deal.discount_percent}</span></div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground" data-testid="deal-provider">{deal.provider} · {deal.badge}</p>
            <p className="mt-1 font-heading text-lg font-bold" data-testid="deal-title">{deal.title}</p>
            <p className="mt-2 min-h-10 text-xs leading-relaxed text-muted-foreground" data-testid="deal-description">{deal.description}</p>
            <div className="mt-4 flex items-end justify-between gap-3">
              <div>
                <p className="text-xs text-muted-foreground">{t("subscriptions.deals.current")} <span className="line-through">{money(deal.current_price, deal.currency, 2)}</span> → {t("subscriptions.deals.alternative")}</p>
                <p className="font-mono text-xl font-bold" data-testid="deal-price">{money(deal.discounted_price, deal.currency, 2)}<span className="text-xs font-normal text-muted-foreground"> / {t("subscriptions.perMonthShort")}</span></p>
                <p className="text-xs text-primary" data-testid="deal-savings">{t("subscriptions.deals.savings")} {money(deal.savings, deal.currency)}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => window.open(deal.url, "_blank", "noopener,noreferrer")} data-testid="deal-open-button">{t("subscriptions.deals.view")} <ArrowUpRight size={13} /></Button>
            </div>
          </Panel>
        ))}
      </div>
      <InstallPrompt />
    </div>
  );
}
