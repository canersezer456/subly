import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import { toast } from "sonner";
import { BellRing, Coins, Download, Eye, Gamepad2, KeyRound, Mail, MailCheck, Moon, Send, ShieldCheck, Sun, Trash2 } from "lucide-react";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { useTheme } from "@/lib/theme";
import { CURRENCIES, useCurrency } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import { money, percent } from "@/lib/format";
import type { AccountExport, DigestPreferences, DigestPreferencesUpdate, DigestPreview, DigestSendResult, GamingBudgetStatus, ReminderPreview, ReminderSendResult, User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LevelPill, PageHeader, Panel, ProgressBar } from "@/components/shared/ui-bits";

export default function Settings() {
  const { t } = useT();
  const user = useOutletContext<User>();
  const { theme, setTheme } = useTheme();
  const { currency, setCurrency } = useCurrency();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const exportData = useMutation({
    mutationFn: () => apiGet<AccountExport>("/account/export"),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: `subly-verilerim-${data.exported_at.slice(0, 10)}.json` });
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t("settings.toast.exportDone"));
    },
    onError: () => toast.error(t("settings.toast.exportFailed")),
  });
  const deleteAccount = useMutation({
    mutationFn: () => apiDelete<void>("/account"),
    onSuccess: () => { queryClient.clear(); toast.success(t("settings.toast.deleted")); window.location.assign("/"); },
    onError: () => toast.error(t("settings.toast.deleteFailed")),
  });

  return (
    <div data-testid="settings-page">
      <PageHeader eyebrow={t("settings.eyebrow")} title={t("settings.title")} description={t("settings.description")} testId="settings-header" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title={t("settings.profile.title")} testId="settings-profile">
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-muted-foreground">{t("settings.profile.name")}</dt><dd data-testid="settings-name">{user.name}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-muted-foreground">{t("settings.profile.email")}</dt><dd data-testid="settings-email">{user.email}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-muted-foreground">{t("settings.profile.loginMethod")}</dt><dd>{user.picture ? t("settings.profile.google") : t("settings.profile.emailPassword")}</dd></div>
          </dl>
        </Panel>

        <Panel title={t("settings.theme.title")} description={t("settings.theme.description")} testId="settings-theme">
          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={() => setTheme("dark")} className={`flex items-center gap-3 rounded-xl border p-4 text-left text-sm transition-colors ${theme === "dark" ? "border-primary bg-primary/10" : "border-border hover:bg-accent"}`} data-testid="theme-dark-option"><Moon size={16} /> {t("settings.theme.dark")} <span className="ml-auto text-xs text-muted-foreground">{t("settings.theme.darkDetail")}</span></button>
            <button type="button" onClick={() => setTheme("light")} className={`flex items-center gap-3 rounded-xl border p-4 text-left text-sm transition-colors ${theme === "light" ? "border-primary bg-primary/10" : "border-border hover:bg-accent"}`} data-testid="theme-light-option"><Sun size={16} /> {t("settings.theme.light")} <span className="ml-auto text-xs text-muted-foreground">{t("settings.theme.lightDetail")}</span></button>
          </div>
        </Panel>

        <Panel title={t("settings.currency.title")} description={t("settings.currency.description")} testId="settings-currency">
          <div className="grid grid-cols-3 gap-3">
            {CURRENCIES.map((c) => (
              <button key={c.code} type="button" onClick={() => setCurrency(c.code)} className={`flex flex-col items-center gap-1 rounded-xl border p-4 text-sm transition-colors ${currency === c.code ? "border-primary bg-primary/10" : "border-border hover:bg-accent"}`} data-testid={`currency-${c.code}-option`}>
                <Coins size={16} />
                <span className="font-mono font-semibold">{c.symbol} {c.code}</span>
              </button>
            ))}
          </div>
          {currency !== "TRY" && (
            <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground" data-testid="currency-approx-note">
              {t("settings.currency.approxNote", { currency })}
            </p>
          )}
        </Panel>

        <Panel title={t("settings.connections.title")} description={t("settings.connections.description")} testId="settings-connections">
          <ul className="space-y-3 text-sm">
            <li className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="connection-google">
              <Mail size={16} className="text-muted-foreground" />
              <div className="flex-1"><p className="font-medium">{t("settings.connections.email.title")}</p><p className="text-xs text-muted-foreground">{t("settings.connections.email.desc")}</p></div>
              <LevelPill level="info">{t("settings.comingSoon")}</LevelPill>
            </li>
            <li className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="connection-bank">
              <KeyRound size={16} className="text-muted-foreground" />
              <div className="flex-1"><p className="font-medium">{t("settings.connections.bank.title")}</p><p className="text-xs text-muted-foreground">{t("settings.connections.bank.desc")}</p></div>
              <LevelPill level="info">{t("settings.comingSoon")}</LevelPill>
            </li>
            <li className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="connection-2fa">
              <ShieldCheck size={16} className="text-muted-foreground" />
              <div className="flex-1"><p className="font-medium">{t("settings.connections.twoFactor.title")}</p><p className="text-xs text-muted-foreground">{t("settings.connections.twoFactor.desc")}</p></div>
              <LevelPill level="info">{t("settings.comingSoon")}</LevelPill>
            </li>
          </ul>
        </Panel>

        <WeeklyDigestPanel email={user.email} />

        <GamingBudgetPanel />

        <Panel title={t("settings.data.title")} description={t("settings.data.description")} testId="settings-data">
          <ul className="mb-5 space-y-2 text-xs leading-relaxed text-muted-foreground" data-testid="privacy-explainer">
            <li><span className="text-foreground">{t("settings.data.why.label")}</span> {t("settings.data.why.text")}</li>
            <li><span className="text-foreground">{t("settings.data.howLong.label")}</span> {t("settings.data.howLong.text")}</li>
            <li><span className="text-foreground">{t("settings.data.howDelete.label")}</span> {t("settings.data.howDelete.text")}</li>
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => exportData.mutate()} disabled={exportData.isPending} data-testid="export-data-button"><Download size={14} /> {exportData.isPending ? t("settings.data.exporting") : t("settings.data.export")}</Button>
            {confirmDelete
              ? <div className="flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs" data-testid="delete-confirm">
                  <span>{t("settings.data.confirmDelete")}</span>
                  <Button size="sm" variant="destructive" onClick={() => deleteAccount.mutate()} disabled={deleteAccount.isPending} data-testid="delete-account-confirm-button">{t("settings.data.confirmYes")}</Button>
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(false)} data-testid="delete-account-cancel-button">{t("settings.data.confirmNo")}</Button>
                </div>
              : <Button variant="ghost" onClick={() => setConfirmDelete(true)} className="text-rose-500 hover:text-rose-400" data-testid="delete-account-button"><Trash2 size={14} /> {t("settings.data.deleteAccount")}</Button>}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function WeeklyDigestPanel({ email }: { email: string }) {
  const { t } = useT();
  const WEEKDAYS = [t("settings.weekday.mon"), t("settings.weekday.tue"), t("settings.weekday.wed"), t("settings.weekday.thu"), t("settings.weekday.fri"), t("settings.weekday.sat"), t("settings.weekday.sun")];
  const queryClient = useQueryClient();
  const prefs = useQuery({ queryKey: ["digest-prefs"], queryFn: () => apiGet<DigestPreferences>("/digest/preferences"), retry: false });
  const [form, setForm] = useState<DigestPreferencesUpdate>({ enabled: false, weekday: 0, hour: 9, reminders_enabled: false, reminder_hour: 8 });
  const [preview, setPreview] = useState<DigestPreview | null>(null);
  const [reminderPreview, setReminderPreview] = useState<ReminderPreview | null>(null);
  useEffect(() => { if (prefs.data) setForm({ enabled: prefs.data.enabled, weekday: prefs.data.weekday, hour: prefs.data.hour, reminders_enabled: prefs.data.reminders_enabled, reminder_hour: prefs.data.reminder_hour }); }, [prefs.data]);

  const save = useMutation({
    mutationFn: (input: DigestPreferencesUpdate) => apiPut<DigestPreferences>("/digest/preferences", input),
    onSuccess: (data) => { queryClient.setQueryData(["digest-prefs"], data); toast.success(data.enabled ? t("settings.digest.toast.on", { day: WEEKDAYS[data.weekday], hour: String(data.hour).padStart(2, "0") }) : t("settings.digest.toast.off")); },
    onError: () => toast.error(t("settings.digest.toast.saveFailed")),
  });
  const sendNow = useMutation({
    mutationFn: () => apiPost<DigestSendResult>("/digest/send-now"),
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["digest-prefs"] }); toast.success(t("settings.digest.toast.sent", { email: r.sent_to })); },
    onError: (err: unknown) => {
      const detail = (err as { body?: { detail?: string } }).body?.detail;
      toast.error(typeof detail === "string" ? detail : t("settings.digest.toast.sendFailed"));
    },
  });
  const loadPreview = useMutation({ mutationFn: () => apiGet<DigestPreview>("/digest/preview"), onSuccess: setPreview, onError: () => toast.error(t("settings.digest.toast.previewFailed")) });
  const loadReminderPreview = useMutation({ mutationFn: () => apiGet<ReminderPreview>("/digest/reminder-preview"), onSuccess: setReminderPreview, onError: () => toast.error(t("settings.digest.toast.previewFailed")) });
  const sendReminder = useMutation({
    mutationFn: () => apiPost<ReminderSendResult>("/digest/send-reminder-now"),
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["digest-prefs"] }); toast.success(t("settings.reminder.toast.sent", { count: r.due_count, email: r.sent_to })); },
    onError: (err: unknown) => {
      const detail = (err as { body?: { detail?: string } }).body?.detail;
      toast.error(typeof detail === "string" ? detail : t("settings.reminder.toast.sendFailed"));
    },
  });

  const update = (patch: Partial<DigestPreferencesUpdate>) => { const next = { ...form, ...patch }; setForm(next); save.mutate(next); };
  const selectClass = "h-9 rounded-lg border border-input bg-background px-2 text-sm";

  return (
    <Panel title={t("settings.digest.title")} description={t("settings.digest.description", { email })} testId="settings-digest" className="lg:col-span-2">
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-sm" data-testid="digest-enabled-row">
          <button type="button" role="switch" aria-checked={form.enabled} onClick={() => update({ enabled: !form.enabled })} className={`relative h-6 w-11 rounded-full transition-colors ${form.enabled ? "bg-primary" : "bg-muted"}`} data-testid="digest-enabled-toggle">
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-[left] ${form.enabled ? "left-[22px]" : "left-0.5"}`} />
          </button>
          <span>{form.enabled ? <span className="flex items-center gap-1.5"><MailCheck size={14} className="text-primary" /> {t("settings.digest.sendWeekly")}</span> : t("settings.off")}</span>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">{t("settings.digest.day")}
          <select value={form.weekday} onChange={(e) => update({ weekday: Number(e.target.value) })} className={selectClass} data-testid="digest-weekday-select">{WEEKDAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">{t("settings.digest.hour")}
          <select value={form.hour} onChange={(e) => update({ hour: Number(e.target.value) })} className={selectClass} data-testid="digest-hour-select">{Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>)}</select>
        </label>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={() => (preview ? setPreview(null) : loadPreview.mutate())} disabled={loadPreview.isPending} data-testid="digest-preview-button"><Eye size={14} /> {preview ? t("settings.digest.closePreview") : t("settings.digest.preview")}</Button>
          <Button onClick={() => sendNow.mutate()} disabled={sendNow.isPending} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="digest-send-now-button"><Send size={14} /> {sendNow.isPending ? t("settings.digest.sending") : t("settings.digest.sendNow")}</Button>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted-foreground" data-testid="digest-status-line">
        {prefs.data?.last_sent_at ? t("settings.digest.lastSent", { date: new Date(prefs.data.last_sent_at).toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" }) }) : t("settings.digest.neverSent")} {t("settings.digest.footnote")}
      </p>
      <div className="mt-5 border-t border-border pt-5" data-testid="reminder-section">
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold"><BellRing size={15} className="text-amber-500" /> {t("settings.reminder.title")}</p>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-sm" data-testid="reminder-enabled-row">
            <button type="button" role="switch" aria-checked={form.reminders_enabled} onClick={() => update({ reminders_enabled: !form.reminders_enabled })} className={`relative h-6 w-11 rounded-full transition-colors ${form.reminders_enabled ? "bg-amber-500" : "bg-muted"}`} data-testid="reminder-enabled-toggle">
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-[left] ${form.reminders_enabled ? "left-[22px]" : "left-0.5"}`} />
            </button>
            <span>{form.reminders_enabled ? t("settings.reminder.sendMorning") : t("settings.off")}</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">{t("settings.digest.hour")}
            <select value={form.reminder_hour} onChange={(e) => update({ reminder_hour: Number(e.target.value) })} className={selectClass} data-testid="reminder-hour-select">{Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>)}</select>
          </label>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" onClick={() => (reminderPreview ? setReminderPreview(null) : loadReminderPreview.mutate())} disabled={loadReminderPreview.isPending} data-testid="reminder-preview-button"><Eye size={14} /> {reminderPreview ? t("settings.digest.closePreview") : t("settings.reminder.previewToday")}</Button>
            <Button variant="outline" onClick={() => sendReminder.mutate()} disabled={sendReminder.isPending} className="border-amber-500/40 text-amber-600 hover:bg-amber-500/10 dark:text-amber-400" data-testid="reminder-send-now-button"><Send size={14} /> {sendReminder.isPending ? t("settings.digest.sending") : t("settings.reminder.sendToday")}</Button>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted-foreground" data-testid="reminder-status-line">
          {t("settings.reminder.footnote")} {prefs.data?.last_reminder_date ? t("settings.reminder.lastSent", { date: new Date(`${prefs.data.last_reminder_date}T12:00:00`).toLocaleDateString("tr-TR", { dateStyle: "medium" }) }) : t("settings.reminder.neverSent")}
        </p>
        {reminderPreview && (
          <div className="mt-4 overflow-hidden rounded-xl border border-border" data-testid="reminder-preview">
            {reminderPreview.due_count === 0 || !reminderPreview.html
              ? <p className="px-4 py-6 text-center text-sm text-muted-foreground" data-testid="reminder-preview-empty">{t("settings.reminder.noneDue")}</p>
              : <>
                  <p className="border-b border-border bg-muted/50 px-4 py-2 text-xs"><span className="text-muted-foreground">{t("settings.digest.subject")}</span> <span data-testid="reminder-preview-subject">{reminderPreview.subject}</span></p>
                  <iframe title={t("settings.reminder.previewTitle")} srcDoc={reminderPreview.html} sandbox="" className="h-[26rem] w-full bg-[#f6f5f0]" data-testid="reminder-preview-frame" />
                </>}
          </div>
        )}
      </div>

      {preview && (
        <div className="mt-4 overflow-hidden rounded-xl border border-border" data-testid="digest-preview">
          <p className="border-b border-border bg-muted/50 px-4 py-2 text-xs"><span className="text-muted-foreground">{t("settings.digest.subject")}</span> <span data-testid="digest-preview-subject">{preview.subject}</span></p>
          <iframe title={t("settings.digest.previewTitle")} srcDoc={preview.html} sandbox="" className="h-[36rem] w-full bg-[#f6f5f0]" data-testid="digest-preview-frame" />
        </div>
      )}
    </Panel>
  );
}


function GamingBudgetPanel() {
  const { t } = useT();
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["gaming", "budget", "settings"], queryFn: () => apiGet<GamingBudgetStatus>("/gaming/budget"), staleTime: 15_000 });
  const [limit, setLimit] = useState<number | "">("");

  useEffect(() => {
    if (status.data?.limit != null) setLimit(status.data.limit);
    else setLimit("");
  }, [status.data]);

  const save = useMutation({
    mutationFn: (value: number) => apiPut<GamingBudgetStatus>("/gaming/budget", { limit: value }),
    onSuccess: () => {
      toast.success(t("settings.gamingBudget.toast.saved"));
      qc.invalidateQueries({ queryKey: ["gaming"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
    onError: () => toast.error(t("settings.gamingBudget.toast.saveFailed")),
  });

  const clear = useMutation({
    mutationFn: () => apiDelete<void>("/gaming/budget"),
    onSuccess: () => {
      toast.success(t("settings.gamingBudget.toast.cleared"));
      qc.invalidateQueries({ queryKey: ["gaming"] });
    },
  });

  const s = status.data;
  const hasLimit = s?.limit != null;

  return (
    <Panel title={t("settings.gamingBudget.title")} description={t("settings.gamingBudget.description")} testId="settings-gaming-budget">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[180px]">
          <label className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{t("settings.gamingBudget.field")}</label>
          <Input
            type="number"
            min="0"
            step="10"
            value={limit}
            onChange={(e) => setLimit(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder={t("settings.gamingBudget.placeholder")}
            data-testid="settings-gaming-budget-input"
          />
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => {
              if (typeof limit !== "number" || limit <= 0) {
                toast.error(t("settings.gamingBudget.toast.invalid"));
                return;
              }
              save.mutate(limit);
            }}
            disabled={save.isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            data-testid="settings-gaming-budget-save"
          >
            <Gamepad2 size={14} /> {hasLimit ? t("common.update") : t("common.save")}
          </Button>
          {hasLimit && (
            <Button variant="outline" onClick={() => clear.mutate()} disabled={clear.isPending} data-testid="settings-gaming-budget-clear">
              {t("common.remove")}
            </Button>
          )}
        </div>
      </div>
      {s && hasLimit && (
        <div className="mt-4" data-testid="settings-gaming-budget-status">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{t("settings.gamingBudget.usage")}</span>
            <span className={`font-mono ${s.exceeded ? "text-rose-500" : s.warning ? "text-amber-500" : "text-foreground"}`}>
              {money(s.spent, "TRY", 0)} / {money(s.limit!, "TRY", 0)} · {percent(s.percent)}
            </span>
          </div>
          <ProgressBar percent={s.percent} exceeded={s.exceeded} />
          <p className="mt-2 text-[11px] text-muted-foreground">
            {t("settings.gamingBudget.note")}
          </p>
        </div>
      )}
      {!hasLimit && (
        <p className="mt-3 rounded-lg border border-border bg-muted/30 p-3 text-[11px] text-muted-foreground">
          {t("settings.gamingBudget.empty")}
        </p>
      )}
    </Panel>
  );
}
