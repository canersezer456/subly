import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Check, FileUp, Landmark, Link2, Lock, Mail, RefreshCw, ScanSearch, TriangleAlert, Unlink, X } from "lucide-react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { dateLabel, money } from "@/lib/format";
import type { BillingCycle, CandidateAcceptPayload, CandidateImportResponse, DiscoveryCandidate, DiscoveryStatus, DuplicateConflict, EmailSyncResponse, MailboxState, MailboxStatus, Provider } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/shared/ui-bits";
import { ProviderMark } from "@/components/brand/ProviderMark";
import { cn } from "@/lib/utils";
import { CURRENCY_OPTIONS, CYCLE_OPTIONS, apiErrorMessage, cycleLabel, decodeStatementBytes, duplicateConflict, statementFileProblem, type Translate } from "@/lib/subscriptionUi";
import { ConfidenceBadge } from "./badges";

const control = "h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm text-foreground outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/25";

function CandidateCard({ candidate, providers, t, onDone }: { candidate: DiscoveryCandidate; providers: Map<string, Provider>; t: Translate; onDone: () => void }) {
  const options = [candidate.provider_id, ...candidate.alternatives].filter((id): id is string => Boolean(id));
  const [providerId, setProviderId] = useState<string>(candidate.provider_id ?? "");
  const provider = providerId ? providers.get(providerId) : undefined;
  const [plan, setPlan] = useState(candidate.suggested_plan ?? "");
  const [price, setPrice] = useState(candidate.suggested_price != null ? String(candidate.suggested_price) : "");
  const [currency, setCurrency] = useState(candidate.currency ?? "TRY");
  const [cycle, setCycle] = useState<BillingCycle>(candidate.billing_cycle ?? "monthly");
  const [renewal, setRenewal] = useState(candidate.renewal_date ?? "");
  const [payment, setPayment] = useState("");
  const [conflict, setConflict] = useState<DuplicateConflict | null>(null);

  const accept = useMutation({
    mutationFn: (confirm: boolean) => {
      const body: CandidateAcceptPayload = { provider_id: providerId || null, plan: plan.trim() || null, price: Number(price), currency, billing_cycle: cycle, renewal_date: renewal, payment_method: payment.trim(), confirm_duplicate: confirm };
      return apiPost(`/subscriptions/candidates/${candidate.id}/accept`, body);
    },
    onSuccess: () => { toast.success(t("subsHub.candidate.acceptedToast")); onDone(); },
    onError: (error) => {
      const dup = duplicateConflict(error);
      if (dup) { setConflict(dup); return; }
      toast.error(apiErrorMessage(error) ?? t("subsHub.candidate.failed"));
    },
  });
  const reject = useMutation({
    mutationFn: () => apiPost(`/subscriptions/candidates/${candidate.id}/reject`),
    onSuccess: () => { toast.success(t("subsHub.candidate.rejectedToast")); onDone(); },
    onError: (error) => toast.error(apiErrorMessage(error) ?? t("subsHub.candidate.failed")),
  });

  const needsProvider = candidate.ambiguous && !providerId;
  const canAccept = !needsProvider && Number(price) > 0 && Boolean(renewal);
  const title = provider?.name ?? candidate.provider_name;

  return (
    <li className="rounded-xl border border-border bg-card p-4" data-testid="discovery-candidate" data-candidate-id={candidate.id}>
      <div className="flex flex-wrap items-start gap-3">
        <ProviderMark name={title} providerId={providerId || null} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold" data-testid="candidate-name">{title}</p>
            <ConfidenceBadge label={candidate.confidence_label} t={t} />
            <span className="rounded-full border border-border bg-muted/50 px-2 py-0.5 text-[10px] text-muted-foreground" data-testid="candidate-source">{[...new Set(candidate.evidence.map((e) => e.source))].map((src) => t(`subsHub.discover.source.${src}`)).join(" + ")}</span>
          </div>
          <p className="mt-0.5 text-xs text-foreground" data-testid="candidate-explanation">{candidate.explanation}</p>
          <ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground" data-testid="candidate-evidence">
            {candidate.evidence.slice(-3).map((e, i) => <li key={i}>{e.summary} · {dateLabel(e.observed_at, true)}</li>)}
          </ul>
        </div>
      </div>

      {candidate.ambiguous && <p className="mt-3 text-xs text-amber-500" data-testid="candidate-ambiguous">{t("subsHub.candidate.ambiguous")}</p>}
      {candidate.possible_duplicates.length > 0 && !conflict && (
        <p className="mt-3 flex items-center gap-1.5 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-500" data-testid="candidate-duplicate-hint">
          <TriangleAlert size={12} /> {t("subsHub.candidate.duplicate", { names: candidate.possible_duplicates.map((d) => d.name).join(", ") })}
        </p>
      )}

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {options.length > 1 || candidate.ambiguous ? (
          <label className="space-y-1 text-[11px] text-muted-foreground">{t("subsHub.candidate.chooseProvider")}
            <select value={providerId} onChange={(e) => setProviderId(e.target.value)} className={control} data-testid="candidate-provider-select">
              {candidate.ambiguous && <option value="">—</option>}
              {options.map((id) => <option key={id} value={id}>{providers.get(id)?.name ?? id}</option>)}
            </select>
          </label>
        ) : null}
        <label className="space-y-1 text-[11px] text-muted-foreground">{t("subsHub.candidate.plan")}
          <Input value={plan} onChange={(e) => setPlan(e.target.value)} list={`plans-${candidate.id}`} maxLength={60} className="h-9" data-testid="candidate-plan" />
          {provider && <datalist id={`plans-${candidate.id}`}>{provider.plans.map((p) => <option key={p} value={p} />)}</datalist>}
        </label>
        <label className="space-y-1 text-[11px] text-muted-foreground">{t("subsHub.candidate.price")}
          <div className="flex gap-1">
            <Input type="number" min="0.01" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} className="h-9" data-testid="candidate-price" />
            <select value={currency} onChange={(e) => setCurrency(e.target.value)} className={cn(control, "w-20")} data-testid="candidate-currency">{CURRENCY_OPTIONS.map((c) => <option key={c}>{c}</option>)}</select>
          </div>
        </label>
        <label className="space-y-1 text-[11px] text-muted-foreground">{t("subsHub.candidate.cycle")}
          <select value={cycle} onChange={(e) => setCycle(e.target.value as BillingCycle)} className={control} data-testid="candidate-cycle">{CYCLE_OPTIONS.map((c) => <option key={c} value={c}>{cycleLabel(t, c)}</option>)}</select>
        </label>
        <label className="space-y-1 text-[11px] text-muted-foreground">{t("subsHub.candidate.renewal")}
          <Input type="date" value={renewal} onChange={(e) => setRenewal(e.target.value)} className="h-9" data-testid="candidate-renewal" />
        </label>
        <label className="space-y-1 text-[11px] text-muted-foreground">{t("subscriptions.field.paymentMethod")}
          <Input value={payment} onChange={(e) => setPayment(e.target.value)} maxLength={60} className="h-9" data-testid="candidate-payment" />
        </label>
      </div>
      {candidate.suggested_price != null && <p className="mt-2 text-[10px] text-muted-foreground">{t("subsHub.candidate.suggestion")} ({money(candidate.suggested_price, candidate.currency ?? "TRY", 2)})</p>}
      {!canAccept && !needsProvider && <p className="mt-2 text-[10px] text-amber-500">{t("subsHub.candidate.needDetails")}</p>}

      {conflict && (
        <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs" role="alert" data-testid="candidate-duplicate-warning">
          <p className="font-semibold text-amber-500">{t("subsHub.add.duplicateTitle")}</p>
          <p className="mt-1">{t("subsHub.add.duplicateBody", { names: conflict.matches.map((m) => m.name).join(", ") })}</p>
          <div className="mt-2 flex gap-2">
            <Button size="sm" variant="outline" onClick={() => accept.mutate(true)} disabled={accept.isPending} data-testid="candidate-duplicate-confirm">{t("subsHub.add.addAnyway")}</Button>
            <Button size="sm" variant="ghost" onClick={() => setConflict(null)}>{t("subsHub.add.cancel")}</Button>
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={() => reject.mutate()} disabled={reject.isPending || accept.isPending} className="text-muted-foreground hover:text-rose-500" data-testid="candidate-reject"><X size={13} /> {t("subsHub.candidate.reject")}</Button>
        <Button size="sm" onClick={() => accept.mutate(false)} disabled={!canAccept || accept.isPending || Boolean(conflict)} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="candidate-accept"><Check size={13} /> {t("subsHub.candidate.accept")}</Button>
      </div>
    </li>
  );
}

type SourceState = MailboxState | "not_integrated" | "manual";

const STATE_STYLE: Record<SourceState, string> = {
  connected: "border-emerald-500/30 bg-emerald-500/10 text-emerald-500",
  available: "border-cyan-500/30 bg-cyan-500/10 text-cyan-500",
  reauth_required: "border-amber-500/30 bg-amber-500/10 text-amber-500",
  not_configured: "border-border bg-muted/60 text-muted-foreground",
  not_integrated: "border-border bg-muted/60 text-muted-foreground",
  manual: "border-indigo-400/30 bg-indigo-400/10 text-indigo-400",
};

function StateBadge({ state, t }: { state: SourceState; t: Translate }) {
  return <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium", STATE_STYLE[state])} data-testid="source-state" data-state={state}>{t(`subsHub.discover.state.${state}`)}</span>;
}

function SourceCard({ icon, title, state, t, testId, children }: { icon: ReactNode; title: string; state: SourceState; t: Translate; testId: string; children: ReactNode }) {
  return (
    <div className={cn("flex flex-col rounded-xl border bg-card p-4", state === "connected" ? "border-emerald-500/30" : "border-border")} data-testid={testId} data-state={state}>
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-semibold">{icon}{title}</p>
        <StateBadge state={state} t={t} />
      </div>
      <div className="mt-2 flex-1 space-y-2 text-xs leading-relaxed text-muted-foreground">{children}</div>
    </div>
  );
}

function MailboxCard({ mailbox, t, onChanged }: { mailbox: MailboxStatus; t: Translate; onChanged: () => void }) {
  const connect = useMutation({
    mutationFn: () => apiPost<{ authorization_url: string }>(`/subscriptions/discovery/email/${mailbox.id}/connect`),
    // Full-page navigation to the provider's consent screen; it redirects back to the backend callback.
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
    onError: (error) => toast.error(apiErrorMessage(error) ?? t("subsHub.discover.email.error.generic")),
  });
  const sync = useMutation({
    mutationFn: () => apiPost<EmailSyncResponse>(`/subscriptions/discovery/email/${mailbox.id}/sync`),
    onSuccess: (r) => {
      if (r.partial) {
        toast.warning(t("subsHub.discover.email.partial", {
          scanned: r.scanned,
          created: r.created,
          merged: r.merged,
          skipped: r.skipped ?? 0,
        }));
      } else {
        toast.success(t("subsHub.discover.email.syncResult", {
          scanned: r.scanned,
          created: r.created,
          merged: r.merged,
        }));
      }
      onChanged();
    },
    onError: (error) => { toast.error(apiErrorMessage(error) ?? t("subsHub.discover.email.error.generic")); onChanged(); },
  });
  const disconnect = useMutation({
    mutationFn: () => apiDelete<void>(`/subscriptions/discovery/email/${mailbox.id}`),
    onSuccess: () => { toast.success(t("subsHub.discover.email.disconnected", { name: mailbox.name })); onChanged(); },
    onError: (error) => toast.error(apiErrorMessage(error) ?? t("subsHub.discover.email.error.generic")),
  });
  const busy = connect.isPending || sync.isPending || disconnect.isPending;

  return (
    <SourceCard testId={`discovery-source-${mailbox.id}`} icon={<Mail size={15} />} title={`${t("subsHub.discover.email.title")} · ${mailbox.name}`} state={mailbox.state} t={t}>
      {mailbox.state === "not_configured" && <p>{t("subsHub.discover.email.notConfiguredBody", { name: mailbox.name })}</p>}
      {mailbox.state === "available" && <p>{t("subsHub.discover.email.availableBody")}</p>}
      {mailbox.state === "reauth_required" && <p className="text-amber-500">{t("subsHub.discover.email.reauthBody")}</p>}
      {mailbox.state === "connected" && (
        <>
          {mailbox.connected_at && <p>{t("subsHub.discover.email.connectedSince", { date: dateLabel(mailbox.connected_at.slice(0, 10), true) })}</p>}
          <p data-testid={`mailbox-last-sync-${mailbox.id}`}>{mailbox.last_sync_at && mailbox.last_sync
            ? t("subsHub.discover.email.lastSync", { date: dateLabel(mailbox.last_sync_at.slice(0, 10), true), scanned: mailbox.last_sync.scanned, created: mailbox.last_sync.created })
            : t("subsHub.discover.email.neverSynced")}</p>
          {mailbox.last_sync?.partial && (
            <p className="text-amber-500" data-testid={`mailbox-partial-${mailbox.id}`}>
              {t("subsHub.discover.email.partial", {
                scanned: mailbox.last_sync.scanned,
                created: mailbox.last_sync.created,
                merged: mailbox.last_sync.merged,
                skipped: mailbox.last_sync.skipped ?? 0,
              })}
            </p>
          )}
        </>
      )}
      {mailbox.state !== "not_configured" && <p className="flex items-start gap-1 text-[11px]"><Lock size={11} className="mt-0.5 shrink-0" /> {t("subsHub.discover.email.scopeNote")}</p>}
      <div className="flex flex-wrap gap-2 pt-1">
        {mailbox.state === "available" && <Button size="sm" onClick={() => connect.mutate()} disabled={busy} data-testid={`mailbox-connect-${mailbox.id}`}><Link2 size={13} /> {t("subsHub.discover.email.connect", { name: mailbox.name })}</Button>}
        {mailbox.state === "reauth_required" && <Button size="sm" onClick={() => connect.mutate()} disabled={busy} data-testid={`mailbox-reconnect-${mailbox.id}`}><RefreshCw size={13} /> {t("subsHub.discover.email.reconnect")}</Button>}
        {mailbox.state === "connected" && <Button size="sm" onClick={() => sync.mutate()} disabled={busy} data-testid={`mailbox-sync-${mailbox.id}`}><ScanSearch size={13} /> {t("subsHub.discover.email.sync")}</Button>}
        {(mailbox.state === "connected" || mailbox.state === "reauth_required") && <Button size="sm" variant="ghost" onClick={() => disconnect.mutate()} disabled={busy} className="text-muted-foreground hover:text-rose-500" data-testid={`mailbox-disconnect-${mailbox.id}`}><Unlink size={13} /> {t("subsHub.discover.email.disconnect")}</Button>}
      </div>
    </SourceCard>
  );
}

const EXAMPLE_FORMAT = "Tarih;Açıklama;Tutar\n2026-01-05;<İŞYERİ ADI>;<TUTAR>\n05.02.2026;<İŞYERİ ADI>;<TUTAR> TL";

export function DiscoveryPanel({ t }: { t: Translate }) {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const status = useQuery({ queryKey: ["subscription-discovery-status"], queryFn: () => apiGet<DiscoveryStatus>("/subscriptions/discovery/status"), retry: false });
  const candidates = useQuery({ queryKey: ["subscription-candidates"], queryFn: () => apiGet<DiscoveryCandidate[]>("/subscriptions/candidates"), retry: false });
  const providers = useQuery({ queryKey: ["subscription-providers"], queryFn: () => apiGet<Provider[]>("/subscriptions/providers?limit=100"), staleTime: 60 * 60_000, retry: false });
  const providerMap = useMemo(() => new Map((providers.data ?? []).map((p) => [p.id, p])), [providers.data]);
  const [text, setText] = useState("");
  const [fileNote, setFileNote] = useState<string | null>(null);
  const [lastImport, setLastImport] = useState<CandidateImportResponse | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" && q.queryKey[0] !== "subscription-providers" });

  // Result of the OAuth round trip (?email=connected|error&provider=…&reason=…): report once, then clean the URL.
  useEffect(() => {
    const outcome = params.get("email");
    if (!outcome) return;
    const name = params.get("provider") === "outlook" ? "Outlook" : "Gmail";
    if (outcome === "connected") toast.success(t("subsHub.discover.email.connected", { name }));
    else {
      const reason = params.get("reason") ?? "";
      const key = `subsHub.discover.email.error.${reason}`;
      const message = t(key);
      toast.error(message === key ? t("subsHub.discover.email.error.generic") : message);
    }
    setParams({ tab: "discover" }, { replace: true });
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once per redirect
  }, [params]);

  const importMutation = useMutation({
    mutationFn: () => apiPost<CandidateImportResponse>("/subscriptions/candidates/import", { text }),
    onSuccess: (result) => { setLastImport(result); setText(""); setFileNote(null); refresh(); },
    onError: (error) => toast.error(apiErrorMessage(error) ?? t("subsHub.discover.import.failed")),
  });

  const pickFile = async (file: File | undefined) => {
    if (!file) return;
    const problem = statementFileProblem(file);
    if (problem) { toast.error(t(problem === "type" ? "subsHub.discover.import.fileType" : "subsHub.discover.import.fileSize")); return; }
    const decoded = decodeStatementBytes(await file.arrayBuffer());
    setText(decoded);
    setFileNote(t("subsHub.discover.import.fileLoaded", { name: file.name, lines: decoded.split(/\r?\n/).filter((l) => l.trim()).length }));
    if (fileInput.current) fileInput.current.value = "";
  };

  const pending = (candidates.data ?? []).filter((c) => c.status === "pending");
  const processed = (candidates.data ?? []).filter((c) => c.status !== "pending");
  const mailboxes = status.data?.email.adapters ?? [];
  const connectedNames = mailboxes.filter((m) => m.state === "connected").map((m) => m.name);

  return (
    <div className="space-y-5" data-testid="discovery-panel">
      <Panel title={t("subsHub.discover.title")} description={t("subsHub.discover.description")} testId="discovery-sources">
        {status.data && (
          <p className={cn("mb-4 rounded-lg border px-3 py-2 text-xs", connectedNames.length ? "border-emerald-500/25 bg-emerald-500/5 text-foreground" : "border-amber-500/25 bg-amber-500/5 text-foreground")} role="status" data-testid="discovery-summary">
            {connectedNames.length ? t("subsHub.discover.summary.connected", { names: connectedNames.join(", ") }) : t("subsHub.discover.summary.none")}
          </p>
        )}
        <ul className="mb-4 grid gap-1.5 text-[11px] text-muted-foreground sm:grid-cols-3" data-testid="discovery-legend">
          <li className="flex items-start gap-2"><StateBadge state="connected" t={t} /> {t("subsHub.discover.legend.connected")}</li>
          <li className="flex items-start gap-2"><StateBadge state="not_configured" t={t} /> {t("subsHub.discover.legend.notConfigured")}</li>
          <li className="flex items-start gap-2"><StateBadge state="manual" t={t} /> {t("subsHub.discover.legend.manual")}</li>
        </ul>

        <div className="grid gap-3 md:grid-cols-3">
          {mailboxes.map((m) => <MailboxCard key={m.id} mailbox={m} t={t} onChanged={refresh} />)}
          <SourceCard testId="discovery-source-bank" icon={<Landmark size={15} />} title={t("subsHub.discover.bank.title")} state="not_integrated" t={t}>
            <p>{t("subsHub.discover.bank.body")}</p>
          </SourceCard>
        </div>
      </Panel>

      <Panel title={t("subsHub.discover.import.title")} description={t("subsHub.discover.import.body")} testId="discovery-source-import" action={<StateBadge state="manual" t={t} />}>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (text.trim()) importMutation.mutate(); }} data-testid="discovery-import-form">
          <div className="flex flex-wrap items-center gap-2">
            <input ref={fileInput} type="file" accept=".csv,.txt,text/csv,text/plain" className="sr-only" id="statement-file" onChange={(e) => void pickFile(e.target.files?.[0])} data-testid="discovery-import-file" />
            <Button type="button" variant="outline" size="sm" onClick={() => fileInput.current?.click()}><FileUp size={13} /> {t("subsHub.discover.import.file")}</Button>
            {fileNote && <span className="text-[11px] text-muted-foreground" data-testid="discovery-import-file-note">{fileNote}</span>}
          </div>
          <textarea value={text} onChange={(e) => { setText(e.target.value); setFileNote(null); }} rows={6} maxLength={500_000} placeholder={t("subsHub.discover.import.placeholder")} className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-xs text-foreground outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/25" aria-label={t("subsHub.discover.import.title")} data-testid="discovery-import-text" />
          <div className="rounded-lg border border-dashed border-border bg-muted/20 p-3" data-testid="discovery-import-example">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-500">{t("subsHub.discover.import.exampleTitle")}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{t("subsHub.discover.import.exampleBody")}</p>
            <pre className="mt-2 overflow-x-auto font-mono text-[11px] text-muted-foreground" aria-hidden="true">{EXAMPLE_FORMAT}</pre>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {text && <Button type="button" variant="ghost" size="sm" onClick={() => { setText(""); setFileNote(null); }}>{t("subsHub.discover.import.clear")}</Button>}
            <Button type="submit" size="sm" disabled={!text.trim() || importMutation.isPending} data-testid="discovery-import-submit"><ScanSearch size={13} /> {t("subsHub.discover.import.submit")}</Button>
          </div>
          {lastImport && (
            <p className="rounded-lg bg-muted/40 px-3 py-2 text-xs" role="status" data-testid="discovery-import-result">
              {lastImport.created + lastImport.merged === 0
                ? t("subsHub.discover.import.none")
                : t("subsHub.discover.import.result", { parsed: lastImport.parsed_transactions, created: lastImport.created, merged: lastImport.merged, skipped: lastImport.skipped_lines })}
            </p>
          )}
        </form>
      </Panel>

      <Panel title={t("subsHub.discover.pending")} testId="discovery-candidates">
        {pending.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="discovery-candidates-empty">{t("subsHub.discover.pendingEmpty")}</p>
        ) : (
          <ul className="space-y-3">
            {pending.map((c) => <CandidateCard key={c.id} candidate={c} providers={providerMap} t={t} onDone={refresh} />)}
          </ul>
        )}
      </Panel>

      {processed.length > 0 && (
        <Panel title={t("subsHub.discover.history")} testId="discovery-history">
          <ul className="divide-y divide-border text-xs">
            {processed.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2">
                <span>{c.provider_name}</span>
                <span className={c.status === "accepted" ? "text-emerald-500" : "text-muted-foreground"}>{c.status === "accepted" ? t("subsHub.discover.accepted") : t("subsHub.discover.rejected")}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
