import { useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ExternalLink, Plus, Search, TriangleAlert, X } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { SUBSCRIPTION_CATEGORIES, USAGE_LABELS, money, subscriptionCategoryLabel, todayIso, usageLabel } from "@/lib/format";
import { rankProviders } from "@/lib/providerCatalog";
import type { BillingCycle, DuplicateConflict, Provider, Subscription, SubscriptionPayload, SubscriptionStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/shared/ui-bits";
import { ProviderMark } from "@/components/brand/ProviderMark";
import { cn } from "@/lib/utils";
import { CURRENCY_OPTIONS, CYCLE_OPTIONS, STATUS_OPTIONS, apiErrorMessage, cycleLabel, duplicateConflict, type Translate } from "@/lib/subscriptionUi";

const control = "h-10 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition-[border-color,box-shadow] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/25";
const CATEGORY_ORDER = ["streaming", "music", "ai", "cloud", "productivity", "gaming", "developer", "sports", "bundle"];

interface Draft {
  name: string;
  category: string;
  plan: string;
  price: string;
  currency: string;
  billing_cycle: BillingCycle;
  renewal_date: string;
  payment_method: string;
  status: SubscriptionStatus;
  usage: SubscriptionPayload["usage"];
  note: string;
}

function draftFor(provider: Provider | null, name: string): Draft {
  return {
    name: provider?.name ?? name,
    category: provider?.subscription_category ?? "Diğer",
    plan: provider && provider.plans.length === 1 ? provider.plans[0] : "",
    price: "",
    currency: provider?.default_currency ?? "TRY",
    billing_cycle: "monthly",
    renewal_date: todayIso(),
    payment_method: "",
    status: "active",
    usage: "active",
    note: "",
  };
}

function Field({ label, children, full }: { label: string; children: ReactNode; full?: boolean }) {
  return (
    <label className={cn("space-y-1.5 text-xs font-medium text-muted-foreground", full && "sm:col-span-2")}>
      <span>{label}</span>
      {children}
    </label>
  );
}

export function AddSubscriptionPanel({ t, onDone }: { t: Translate; onDone: () => void }) {
  const queryClient = useQueryClient();
  const providers = useQuery({ queryKey: ["subscription-providers"], queryFn: () => apiGet<Provider[]>("/subscriptions/providers?limit=100"), staleTime: 60 * 60_000, retry: false });
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Provider | null>(null);
  const [custom, setCustom] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [conflict, setConflict] = useState<DuplicateConflict | null>(null);

  const results = useMemo(() => rankProviders(providers.data ?? [], query), [providers.data, query]);
  const grouped = useMemo(() => CATEGORY_ORDER.map((c) => [c, (providers.data ?? []).filter((p) => p.category === c)] as const).filter(([, list]) => list.length > 0), [providers.data]);

  const pick = (provider: Provider | null) => {
    setSelected(provider);
    setCustom(provider === null);
    setDraft(draftFor(provider, query.trim()));
    setConflict(null);
  };
  const reset = () => { setSelected(null); setCustom(false); setDraft(null); setConflict(null); };
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => (d ? { ...d, [key]: value } : d));

  const create = useMutation({
    mutationFn: (confirm: boolean) => {
      const d = draft!;
      const payload: SubscriptionPayload = {
        name: d.name.trim(),
        category: d.category,
        price: Number(d.price),
        currency: d.currency,
        renewal_date: d.renewal_date,
        payment_method: d.payment_method.trim(),
        cancellation_url: selected?.manage_url ?? "",
        billing_cycle: d.billing_cycle,
        usage: d.usage,
        status: d.status,
        provider_id: selected?.id ?? null,
        plan: d.plan.trim() || null,
        note: d.note.trim(),
        confirm_duplicate: confirm,
      };
      return apiPost<Subscription>("/subscriptions", payload);
    },
    onSuccess: () => {
      toast.success(t("subsHub.add.done"));
      queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" && q.queryKey[0] !== "subscription-providers" });
      reset();
      setQuery("");
      onDone();
    },
    onError: (error) => {
      const dup = duplicateConflict(error);
      if (dup) { setConflict(dup); return; }
      toast.error(apiErrorMessage(error) ?? t("subsHub.add.failed"));
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft || draft.name.trim().length < 2) { toast.error(t("subsHub.add.pickFirst")); return; }
    create.mutate(false);
  };

  return (
    <Panel title={t("subsHub.add.title")} description={t("subsHub.add.description")} testId="add-subscription-panel">
      {!draft ? (
        <div className="space-y-4">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("subsHub.add.searchPlaceholder")} className="h-11 pl-9" autoFocus data-testid="provider-search-input" aria-label={t("subsHub.add.searchPlaceholder")} />
          </div>
          {query.trim() ? (
            <div className="space-y-2" data-testid="provider-search-results">
              {results.slice(0, 8).map((p) => (
                <button key={p.id} type="button" onClick={() => pick(p)} className="flex w-full items-center gap-3 rounded-xl border border-border bg-card px-3 py-2 text-left transition-colors hover:border-primary/40" data-testid={`provider-option-${p.id}`}>
                  <ProviderMark name={p.name} providerId={p.id} size="sm" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">{p.name}</span>
                    <span className="block truncate text-[11px] text-muted-foreground">{t(`subsHub.cat.${p.category}`)}{p.plans.length > 0 && ` · ${p.plans.join(", ")}`}</span>
                  </span>
                </button>
              ))}
              {results.length === 0 && <p className="text-xs text-muted-foreground" data-testid="provider-no-results">{t("subsHub.add.noResults")}</p>}
              {query.trim().length >= 2 && (
                <Button type="button" variant="outline" size="sm" onClick={() => pick(null)} data-testid="provider-custom-button"><Plus size={13} /> {t("subsHub.add.custom", { name: query.trim() })}</Button>
              )}
            </div>
          ) : (
            <div className="space-y-4" data-testid="provider-catalog">
              {grouped.map(([category, list]) => (
                <div key={category}>
                  <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{t(`subsHub.cat.${category}`)}</p>
                  <div className="flex flex-wrap gap-2">
                    {list.map((p) => (
                      <button key={p.id} type="button" onClick={() => pick(p)} className="flex items-center gap-2 rounded-full border border-border bg-card py-1 pl-1 pr-3 text-xs transition-colors hover:border-primary/40" data-testid={`provider-chip-${p.id}`}>
                        <ProviderMark name={p.name} providerId={p.id} size="sm" />{p.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="add-subscription-form">
          <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/30 p-3">
            <ProviderMark name={draft.name || query} providerId={selected?.id} />
            <div className="min-w-0 flex-1">
              <p className="text-[11px] text-muted-foreground">{t("subsHub.add.selected")}</p>
              <p className="truncate text-sm font-semibold" data-testid="add-selected-provider">{selected?.name ?? draft.name}</p>
              {selected && <a href={selected.manage_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline">{t("subsHub.add.manageLink")} <ExternalLink size={10} /></a>}
              {selected?.note && <p className="mt-1 text-[11px] text-muted-foreground">{selected.note}</p>}
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={reset} data-testid="add-change-provider"><X size={13} /> {t("subsHub.add.change")}</Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {custom && (
              <>
                <Field label={t("subsHub.add.name")}><Input value={draft.name} onChange={(e) => set("name", e.target.value)} required minLength={2} maxLength={80} data-testid="add-field-name" /></Field>
                <Field label={t("subscriptions.field.category")}>
                  <select value={draft.category} onChange={(e) => set("category", e.target.value)} className={control} data-testid="add-field-category">
                    {SUBSCRIPTION_CATEGORIES.map((c) => <option key={c} value={c}>{subscriptionCategoryLabel(t, c)}</option>)}
                  </select>
                </Field>
              </>
            )}
            <Field label={t("subsHub.add.plan")}>
              <Input value={draft.plan} onChange={(e) => set("plan", e.target.value)} list="add-plan-options" placeholder={t("subsHub.add.planPlaceholder")} maxLength={60} data-testid="add-field-plan" />
              {selected && selected.plans.length > 0 && <datalist id="add-plan-options">{selected.plans.map((p) => <option key={p} value={p} />)}</datalist>}
            </Field>
            <Field label={t("subsHub.add.status")}>
              <select value={draft.status} onChange={(e) => set("status", e.target.value as SubscriptionStatus)} className={control} data-testid="add-field-status">
                {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{t(`subsHub.status.${s}`)}</option>)}
              </select>
            </Field>
            <Field label={t("subscriptions.field.price")}>
              <Input type="number" inputMode="decimal" min="0.01" max="100000" step="0.01" value={draft.price} onChange={(e) => set("price", e.target.value)} required data-testid="add-field-price" />
            </Field>
            <Field label={t("subscriptions.field.currency")}>
              <select value={draft.currency} onChange={(e) => set("currency", e.target.value)} className={control} data-testid="add-field-currency">
                {CURRENCY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label={t("subscriptions.field.billingCycle")}>
              <select value={draft.billing_cycle} onChange={(e) => set("billing_cycle", e.target.value as BillingCycle)} className={control} data-testid="add-field-cycle">
                {CYCLE_OPTIONS.map((c) => <option key={c} value={c}>{cycleLabel(t, c)}</option>)}
              </select>
            </Field>
            <Field label={t("subscriptions.field.renewalDate")}>
              <Input type="date" value={draft.renewal_date} onChange={(e) => set("renewal_date", e.target.value)} required data-testid="add-field-renewal" />
            </Field>
            <Field label={t("subscriptions.field.paymentMethod")}>
              <Input value={draft.payment_method} onChange={(e) => set("payment_method", e.target.value)} maxLength={60} data-testid="add-field-payment" />
            </Field>
            <Field label={t("subscriptions.field.usage")}>
              <select value={draft.usage} onChange={(e) => set("usage", e.target.value as Draft["usage"])} className={control} data-testid="add-field-usage">
                {Object.keys(USAGE_LABELS).map((u) => <option key={u} value={u}>{usageLabel(t, u)}</option>)}
              </select>
            </Field>
            <Field label={t("subsHub.add.note")} full>
              <textarea value={draft.note} onChange={(e) => set("note", e.target.value)} maxLength={500} rows={2} className={cn(control, "h-auto py-2")} data-testid="add-field-note" />
            </Field>
          </div>
          <p className="text-[11px] text-muted-foreground" data-testid="add-pricing-note">{t("subsHub.add.pricingNote")}</p>

          {conflict && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs" role="alert" data-testid="add-duplicate-warning">
              <p className="flex items-center gap-1.5 font-semibold text-amber-500"><TriangleAlert size={13} /> {t("subsHub.add.duplicateTitle")}</p>
              <p className="mt-1 text-foreground">{t("subsHub.add.duplicateBody", { names: conflict.matches.map((m) => (m.price != null ? `${m.name} (${money(m.price, m.currency, 2)})` : m.name)).join(", ") })}</p>
              <div className="mt-2 flex gap-2">
                <Button type="button" size="sm" variant="outline" onClick={() => create.mutate(true)} disabled={create.isPending} data-testid="add-duplicate-confirm">{t("subsHub.add.addAnyway")}</Button>
                <Button type="button" size="sm" variant="ghost" onClick={() => setConflict(null)} data-testid="add-duplicate-cancel">{t("subsHub.add.cancel")}</Button>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <Button type="submit" disabled={create.isPending || Boolean(conflict)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="add-submit"><Plus size={14} /> {t("subsHub.add.submit")}</Button>
          </div>
        </form>
      )}
    </Panel>
  );
}
