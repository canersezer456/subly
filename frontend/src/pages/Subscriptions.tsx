import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowUpRight, CreditCard, ExternalLink, Gift, History, Pencil, Plus, RefreshCw, ScanSearch, Search, Sparkles, Trash2 } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { useCrud } from "@/hooks/useCrud";
import { SUBSCRIPTION_CATEGORIES, USAGE_LABELS, dateLabel, money, paymentMethodLabel, subscriptionCategoryLabel, todayIso, usageLabel } from "@/lib/format";
import { toTry, useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { Deal, Subscription, SubscriptionInsights, SubscriptionPayload } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProviderMark } from "@/components/brand/ProviderMark";
import { InstallPrompt } from "@/components/mobile/InstallPrompt";
import { EntityDialog, translatedOpts, type FieldDef, type FormValues } from "@/components/shared/EntityDialog";
import { EmptyState, LevelPill, PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";
import { AddSubscriptionPanel } from "@/components/subscriptions/AddSubscriptionPanel";
import { DiscoveryPanel } from "@/components/subscriptions/DiscoveryPanel";
import { InsightsPanel } from "@/components/subscriptions/InsightsPanel";
import { SourceBadge } from "@/components/subscriptions/badges";
import { CURRENCY_OPTIONS, CYCLE_OPTIONS, STATUS_OPTIONS, cycleLabel, type Translate } from "@/lib/subscriptionUi";
import { cn } from "@/lib/utils";

const CYCLE_MONTHS: Record<string, number> = { monthly: 1, quarterly: 3, yearly: 12 };
const monthlyTry = (s: Subscription) => toTry(s.price, s.currency) / (CYCLE_MONTHS[s.billing_cycle] ?? 1);
const ALL_CATEGORIES = "__all__";
type Tab = "list" | "discover" | "add" | "deals";
const TABS: Tab[] = ["list", "discover", "add", "deals"];

export default function Subscriptions() {
  const { t } = useT();
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  // "scan" was the old name of the discovery tab; keep old links working.
  const tab: Tab = requested === "scan" ? "discover" : TABS.includes(requested as Tab) ? (requested as Tab) : "list";
  const setTab = (next: Tab) => setParams(next === "list" ? {} : { tab: next }, { replace: true });
  const crud = useCrud<Subscription, SubscriptionPayload>("subscriptions", "/subscriptions");
  const insights = useQuery({ queryKey: ["subscription-insights"], queryFn: () => apiGet<SubscriptionInsights>("/subscriptions/insights"), retry: false });
  const { display } = useMoney();
  const [editing, setEditing] = useState<Subscription | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(ALL_CATEGORIES);

  const fields: FieldDef[] = [
    { name: "name", label: t("subscriptions.field.name"), required: true, full: true },
    { name: "plan", label: t("subsHub.add.plan"), placeholder: t("subsHub.add.planPlaceholder") },
    { name: "status", label: t("subsHub.add.status"), type: "select", options: STATUS_OPTIONS.map((s) => ({ value: s, label: t(`subsHub.status.${s}`) })) },
    { name: "category", label: t("subscriptions.field.category"), type: "select", options: translatedOpts(SUBSCRIPTION_CATEGORIES, (v) => subscriptionCategoryLabel(t, v)) },
    { name: "price", label: t("subscriptions.field.price"), type: "number", required: true },
    { name: "currency", label: t("subscriptions.field.currency"), type: "select", options: CURRENCY_OPTIONS.map((c) => ({ value: c, label: c })) },
    { name: "billing_cycle", label: t("subscriptions.field.billingCycle"), type: "select", options: CYCLE_OPTIONS.map((c) => ({ value: c, label: cycleLabel(t, c) })) },
    { name: "renewal_date", label: t("subscriptions.field.renewalDate"), type: "date", required: true },
    { name: "payment_method", label: t("subscriptions.field.paymentMethod"), type: "text" },
    { name: "usage", label: t("subscriptions.field.usage"), type: "select", options: translatedOpts(Object.keys(USAGE_LABELS), (v) => usageLabel(t, v)), hint: t("subscriptions.field.usageHint") },
    { name: "cancellation_url", label: t("subscriptions.field.cancellationUrl"), type: "url", full: true },
    { name: "note", label: t("subsHub.add.note"), type: "textarea" },
  ];

  const deals = useQuery({ queryKey: ["deals"], queryFn: () => apiGet<Deal[]>("/subscriptions/deals"), enabled: tab === "deals", retry: false });

  const active = crud.items.filter((s) => s.status === "active");
  const monthly = active.reduce((sum, s) => sum + monthlyTry(s), 0);
  const filtered = useMemo(() => crud.items.filter((s) => (category === ALL_CATEGORIES || s.category === category) && s.name.toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR"))), [crud.items, category, search]);
  const legacyToReview = crud.items.filter((s) => s.legacy && !s.legacy_reviewed);

  const reviewLegacy = useMutation({
    mutationFn: (id: string) => apiPost<Subscription>(`/subscriptions/${id}/review`),
    onSuccess: () => { toast.success(t("subsHub.legacy.confirmed")); crud.refresh(); },
    onError: () => toast.error(t("crud.updateFailed")),
  });

  const close = () => setEditing(null);
  const initial: FormValues = editing
    ? { name: editing.name, plan: editing.plan ?? "", status: editing.status, category: editing.category, price: editing.price, currency: editing.currency, billing_cycle: editing.billing_cycle, renewal_date: editing.renewal_date, payment_method: editing.payment_method, usage: editing.usage, cancellation_url: editing.cancellation_url, note: editing.note ?? "" }
    : { name: "", plan: "", status: "active", category: "Eğlence", price: 0, currency: "TRY", billing_cycle: "monthly", renewal_date: todayIso(), payment_method: "", usage: "active", cancellation_url: "", note: "" };
  const submit = (values: FormValues) => {
    if (!editing) return;
    crud.update.mutate({ id: editing.id, input: values as unknown as SubscriptionPayload }, { onSuccess: close });
  };
  const openManagePage = (sub: Subscription) => window.open(sub.cancellation_url, "_blank", "noopener,noreferrer");

  const tabs = [
    { id: "list" as const, label: t("subsHub.tab.list"), icon: RefreshCw },
    { id: "discover" as const, label: t("subsHub.tab.discover"), icon: ScanSearch },
    { id: "add" as const, label: t("subsHub.tab.add"), icon: Plus },
    { id: "deals" as const, label: t("subscriptions.tab.deals"), icon: Gift },
  ];

  return (
    <div data-testid="subscriptions-page">
      <PageHeader eyebrow={t("subscriptions.eyebrow")} title={t("subscriptions.title")} description={t("subscriptions.description")} testId="subscriptions-header"
        actions={<Button onClick={() => setTab("add")} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-subscription-button"><Plus size={15} /> {t("subscriptions.action.add")}</Button>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="subscription-stats">
        <StatCard label={t("subscriptions.stat.monthly")} value={display(monthly)} detail={t("subscriptions.stat.monthlyDetail", { count: active.length })} icon={<RefreshCw size={17} />} tone="emerald" testId="subs-monthly" />
        <StatCard label={t("subscriptions.stat.yearly")} value={display(monthly * 12)} detail={t("subscriptions.stat.yearlyDetail")} icon={<CreditCard size={17} />} tone="indigo" testId="subs-yearly" />
        <StatCard label={t("subscriptions.stat.unused")} value={String(active.filter((s) => s.usage === "unused").length)} detail={t("subscriptions.stat.unusedDetail", { count: active.filter((s) => s.usage === "rarely").length })} icon={<Sparkles size={17} />} tone="amber" to="/savings" testId="subs-unused" />
      </section>

      <div className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-border bg-card p-1 sm:w-fit" role="tablist" data-testid="subscription-tabs">
        {tabs.map((tabItem) => {
          const Icon = tabItem.icon;
          return (
            <button key={tabItem.id} type="button" role="tab" aria-selected={tab === tabItem.id} onClick={() => setTab(tabItem.id)} className={cn("flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-xs transition-colors sm:flex-none", tab === tabItem.id ? "bg-primary/12 font-medium text-primary" : "text-muted-foreground hover:text-foreground")} data-testid={`nav-${tabItem.id}-tab`}>
              <Icon size={14} />{tabItem.label}
            </button>
          );
        })}
      </div>

      {tab === "list" && (
        <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
          <div className="space-y-4">
            {legacyToReview.length > 0 && (
              <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 p-4" data-testid="legacy-review-banner">
                <p className="flex items-center gap-2 text-sm font-semibold text-amber-500"><History size={15} /> {t("subsHub.legacy.title")}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t("subsHub.legacy.description", { count: legacyToReview.length })}</p>
              </div>
            )}
            <Panel testId="subscription-list" title={t("subscriptions.list.title")} description={t("subscriptions.list.description", { count: filtered.length })}
              action={<div className="flex gap-2">
                <div className="relative"><Search size={14} className="absolute left-2.5 top-2.5 text-muted-foreground" /><Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("subscriptions.search")} className="h-9 w-36 pl-8 text-sm" data-testid="subscription-search-input" /></div>
                <select value={category} onChange={(e) => setCategory(e.target.value)} className="h-9 rounded-lg border border-input bg-background px-2 text-sm" data-testid="filter-category-select"><option value={ALL_CATEGORIES}>{t("common.all")}</option>{SUBSCRIPTION_CATEGORIES.map((c) => <option key={c} value={c}>{subscriptionCategoryLabel(t, c)}</option>)}</select>
              </div>}>
              {crud.isError ? <div role="alert" data-testid="subscriptions-error">{t("common.error")} <Button onClick={() => crud.retry()}>{t("common.retry")}</Button></div>
                : crud.isLoading ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="subscriptions-loading">{t("common.loading")}</p>
                : crud.items.length === 0 ? <EmptyState title={t("subsHub.empty.title")} description={t("subsHub.empty.description")} testId="subscription-empty-state" action={<div className="flex flex-wrap justify-center gap-2"><Button onClick={() => setTab("add")} data-testid="empty-add-button"><Plus size={14} /> {t("subscriptions.action.add")}</Button><Button variant="outline" onClick={() => setTab("discover")} data-testid="empty-discover-button"><ScanSearch size={14} /> {t("subsHub.tab.discover")}</Button></div>} />
                : filtered.length === 0 ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="subscription-filter-empty">{t("subsHub.empty.filtered")}</p>
                : (
                <ul className="divide-y divide-border">
                  {filtered.map((sub) => (
                    <li key={sub.id} className="flex flex-wrap items-center gap-3 py-3.5" data-testid="subscription-item">
                      <ProviderMark name={sub.name} providerId={sub.provider_id} />
                      <div className="min-w-[9rem] flex-1">
                        <p className="flex flex-wrap items-center gap-1.5 text-sm font-medium" data-testid="subscription-name">{sub.name}{sub.plan && <span className="text-xs font-normal text-muted-foreground">· {sub.plan}</span>}</p>
                        <p className="text-xs text-muted-foreground">{subscriptionCategoryLabel(t, sub.category)}{sub.payment_method && ` · ${paymentMethodLabel(t, sub.payment_method)}`} · {t("subscriptions.item.renewal")} {dateLabel(sub.renewal_date)}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <SourceBadge source={sub.source} t={t} />
                          {sub.legacy && !sub.legacy_reviewed && (
                            <Button variant="outline" size="xs" onClick={() => reviewLegacy.mutate(sub.id)} disabled={reviewLegacy.isPending} data-testid="legacy-confirm-button">{t("subsHub.legacy.confirm")}</Button>
                          )}
                        </div>
                      </div>
                      <LevelPill level={sub.usage === "unused" ? "red" : sub.usage === "rarely" ? "yellow" : "green"} testId="subscription-usage-badge">{usageLabel(t, sub.usage)}</LevelPill>
                      <div className="w-28 text-right">
                        <p className="font-mono text-sm font-semibold" data-testid="subscription-price">{money(sub.price, sub.currency, 2)}</p>
                        <p className="text-[11px] text-muted-foreground">{cycleLabel(t, sub.billing_cycle)}{sub.status !== "active" && <span className={cn("ml-1", sub.status === "cancelled" ? "text-rose-500" : "text-amber-500")} data-testid="subscription-status-badge">· {t(`subsHub.status.${sub.status}`)}</span>}</p>
                      </div>
                      <div className="flex gap-0.5">
                        <Button variant="ghost" size="icon-sm" onClick={() => setEditing(sub)} aria-label={t("common.edit")} data-testid="edit-subscription-button"><Pencil size={14} /></Button>
                        <Button variant="ghost" size="icon-sm" onClick={() => openManagePage(sub)} disabled={!sub.cancellation_url} className="text-rose-500" aria-label={t("subscriptions.item.openCancelPage")} title={t("subscriptions.item.openCancelPage")} data-testid="one-click-cancel-button"><ExternalLink size={14} /></Button>
                        <Button variant="ghost" size="icon-sm" onClick={() => crud.remove.mutate(sub.id)} className="text-muted-foreground hover:text-rose-500" aria-label={t("common.delete")} data-testid="delete-subscription-button"><Trash2 size={14} /></Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
          {insights.data ? <InsightsPanel insights={insights.data} t={t} /> : insights.isError ? <Panel testId="subscription-insights-error"><p className="text-sm text-muted-foreground">{t("common.error")}</p></Panel> : null}
        </div>
      )}

      {tab === "discover" && <DiscoveryPanel t={t} />}

      {tab === "add" && <AddSubscriptionPanel t={t} onDone={() => setTab("list")} />}

      {tab === "deals" && <DealsPanel deals={deals.data ?? []} t={t} />}

      <EntityDialog open={editing !== null} onClose={close} title={t("subscriptions.dialog.editTitle")} fields={fields} initial={initial} onSubmit={submit} busy={crud.update.isPending} submitLabel={t("common.save")} testId="subscription-dialog" />
    </div>
  );
}

function DealsPanel({ deals, t }: { deals: Deal[]; t: Translate }) {
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
