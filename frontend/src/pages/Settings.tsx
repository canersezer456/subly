import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import { toast } from "sonner";
import { BellRing, Download, Eye, Gamepad2, KeyRound, Mail, MailCheck, Moon, Send, ShieldCheck, Sun, Trash2 } from "lucide-react";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { useTheme } from "@/lib/theme";
import { money, percent } from "@/lib/format";
import type { AccountExport, DigestPreferences, DigestPreferencesUpdate, DigestPreview, DigestSendResult, GamingBudgetStatus, ReminderPreview, ReminderSendResult, User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LevelPill, PageHeader, Panel, ProgressBar } from "@/components/shared/ui-bits";

export default function Settings() {
  const user = useOutletContext<User>();
  const { theme, setTheme } = useTheme();
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
      toast.success("Verilerin indirildi");
    },
    onError: () => toast.error("Dışa aktarma başarısız"),
  });
  const deleteAccount = useMutation({
    mutationFn: () => apiDelete<void>("/account"),
    onSuccess: () => { queryClient.clear(); toast.success("Hesabın ve tüm verilerin silindi"); window.location.assign("/"); },
    onError: () => toast.error("Hesap silinemedi"),
  });

  return (
    <div data-testid="settings-page">
      <PageHeader eyebrow="Ayarlar" title="Hesap, gizlilik ve görünüm" description="Verilerinin neden kullanıldığını, ne kadar saklandığını ve nasıl silebileceğini burada açıkça görürsün." testId="settings-header" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Profil" testId="settings-profile">
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-muted-foreground">Ad</dt><dd data-testid="settings-name">{user.name}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-muted-foreground">E-posta</dt><dd data-testid="settings-email">{user.email}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-muted-foreground">Giriş yöntemi</dt><dd>{user.picture ? "Google (OAuth)" : "E-posta + şifre"}</dd></div>
          </dl>
        </Panel>

        <Panel title="Görünüm" description="Tema tercihin bu cihazda saklanır" testId="settings-theme">
          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={() => setTheme("dark")} className={`flex items-center gap-3 rounded-xl border p-4 text-left text-sm transition-colors ${theme === "dark" ? "border-primary bg-primary/10" : "border-border hover:bg-accent"}`} data-testid="theme-dark-option"><Moon size={16} /> Koyu <span className="ml-auto text-xs text-muted-foreground">Slate + zümrüt</span></button>
            <button type="button" onClick={() => setTheme("light")} className={`flex items-center gap-3 rounded-xl border p-4 text-left text-sm transition-colors ${theme === "light" ? "border-primary bg-primary/10" : "border-border hover:bg-accent"}`} data-testid="theme-light-option"><Sun size={16} /> Açık <span className="ml-auto text-xs text-muted-foreground">Krem + yeşil</span></button>
          </div>
        </Panel>

        <Panel title="Bağlı hesaplar ve izinler" description="Açık izin olmadan hiçbir veriye erişilmez" testId="settings-connections">
          <ul className="space-y-3 text-sm">
            <li className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="connection-google">
              <Mail size={16} className="text-muted-foreground" />
              <div className="flex-1"><p className="font-medium">Gmail / Outlook abonelik tespiti</p><p className="text-xs text-muted-foreground">E-posta okuma izni · yalnızca abonelik e-postaları · istediğin an kaldır</p></div>
              <LevelPill level="info">Yakında</LevelPill>
            </li>
            <li className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="connection-bank">
              <KeyRound size={16} className="text-muted-foreground" />
              <div className="flex-1"><p className="font-medium">Banka bağlantısı</p><p className="text-xs text-muted-foreground">Yalnızca hareket okuma izni · kart numarası saklanmaz</p></div>
              <LevelPill level="info">Yakında</LevelPill>
            </li>
            <li className="flex items-center gap-3 rounded-xl border border-border p-3" data-testid="connection-2fa">
              <ShieldCheck size={16} className="text-muted-foreground" />
              <div className="flex-1"><p className="font-medium">İki adımlı doğrulama (2FA)</p><p className="text-xs text-muted-foreground">Şifren PBKDF2 ile hash'lenir; oturum httpOnly + Secure çerezde tutulur</p></div>
              <LevelPill level="info">Yakında</LevelPill>
            </li>
          </ul>
        </Panel>

        <WeeklyDigestPanel email={user.email} />

        <GamingBudgetPanel />

        <Panel title="Verilerin" description="Neden kullanıyoruz, ne kadar saklıyoruz, nasıl silersin" testId="settings-data">
          <ul className="mb-5 space-y-2 text-xs leading-relaxed text-muted-foreground" data-testid="privacy-explainer">
            <li><span className="text-foreground">Neden?</span> Gelir, gider, abonelik ve fatura kayıtların yalnızca sana özet, uyarı ve tasarruf önerisi üretmek için işlenir. Reklam veya üçüncü taraflarla paylaşım yok.</li>
            <li><span className="text-foreground">Ne kadar süre?</span> Hesabın açık olduğu sürece. AI asistanı sorgularında verilerin yalnızca cevap üretimi için modele iletilir, model tarafında saklanmaz.</li>
            <li><span className="text-foreground">Nasıl silerim?</span> Aşağıdaki buton hesabını, oturumlarını ve tüm kayıtlarını kalıcı olarak siler.</li>
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => exportData.mutate()} disabled={exportData.isPending} data-testid="export-data-button"><Download size={14} /> {exportData.isPending ? "Hazırlanıyor…" : "Verilerimi indir (JSON)"}</Button>
            {confirmDelete
              ? <div className="flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs" data-testid="delete-confirm">
                  <span>Emin misin? Bu işlem geri alınamaz.</span>
                  <Button size="sm" variant="destructive" onClick={() => deleteAccount.mutate()} disabled={deleteAccount.isPending} data-testid="delete-account-confirm-button">Evet, sil</Button>
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(false)} data-testid="delete-account-cancel-button">Vazgeç</Button>
                </div>
              : <Button variant="ghost" onClick={() => setConfirmDelete(true)} className="text-rose-500 hover:text-rose-400" data-testid="delete-account-button"><Trash2 size={14} /> Hesabımı ve verilerimi sil</Button>}
          </div>
        </Panel>
      </div>
    </div>
  );
}

const WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

function WeeklyDigestPanel({ email }: { email: string }) {
  const queryClient = useQueryClient();
  const prefs = useQuery({ queryKey: ["digest-prefs"], queryFn: () => apiGet<DigestPreferences>("/digest/preferences"), retry: false });
  const [form, setForm] = useState<DigestPreferencesUpdate>({ enabled: false, weekday: 0, hour: 9, reminders_enabled: false, reminder_hour: 8 });
  const [preview, setPreview] = useState<DigestPreview | null>(null);
  const [reminderPreview, setReminderPreview] = useState<ReminderPreview | null>(null);
  useEffect(() => { if (prefs.data) setForm({ enabled: prefs.data.enabled, weekday: prefs.data.weekday, hour: prefs.data.hour, reminders_enabled: prefs.data.reminders_enabled, reminder_hour: prefs.data.reminder_hour }); }, [prefs.data]);

  const save = useMutation({
    mutationFn: (input: DigestPreferencesUpdate) => apiPut<DigestPreferences>("/digest/preferences", input),
    onSuccess: (data) => { queryClient.setQueryData(["digest-prefs"], data); toast.success(data.enabled ? `Haftalık özet açık · ${WEEKDAYS[data.weekday]} ${String(data.hour).padStart(2, "0")}:00` : "Haftalık özet kapatıldı"); },
    onError: () => toast.error("Tercih kaydedilemedi"),
  });
  const sendNow = useMutation({
    mutationFn: () => apiPost<DigestSendResult>("/digest/send-now"),
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["digest-prefs"] }); toast.success(`Özet ${r.sent_to} adresine gönderildi`); },
    onError: (err: unknown) => {
      const detail = (err as { body?: { detail?: string } }).body?.detail;
      toast.error(typeof detail === "string" ? detail : "E-posta gönderilemedi");
    },
  });
  const loadPreview = useMutation({ mutationFn: () => apiGet<DigestPreview>("/digest/preview"), onSuccess: setPreview, onError: () => toast.error("Önizleme oluşturulamadı") });
  const loadReminderPreview = useMutation({ mutationFn: () => apiGet<ReminderPreview>("/digest/reminder-preview"), onSuccess: setReminderPreview, onError: () => toast.error("Önizleme oluşturulamadı") });
  const sendReminder = useMutation({
    mutationFn: () => apiPost<ReminderSendResult>("/digest/send-reminder-now"),
    onSuccess: (r) => { queryClient.invalidateQueries({ queryKey: ["digest-prefs"] }); toast.success(`${r.due_count} ödeme için hatırlatma ${r.sent_to} adresine gönderildi`); },
    onError: (err: unknown) => {
      const detail = (err as { body?: { detail?: string } }).body?.detail;
      toast.error(typeof detail === "string" ? detail : "Hatırlatma gönderilemedi");
    },
  });

  const update = (patch: Partial<DigestPreferencesUpdate>) => { const next = { ...form, ...patch }; setForm(next); save.mutate(next); };
  const selectClass = "h-9 rounded-lg border border-input bg-background px-2 text-sm";

  return (
    <Panel title="Haftalık özet e-postası" description={`Yaklaşan ödemeler ve tasarruf ipuçları · ${email}`} testId="settings-digest" className="lg:col-span-2">
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-sm" data-testid="digest-enabled-row">
          <button type="button" role="switch" aria-checked={form.enabled} onClick={() => update({ enabled: !form.enabled })} className={`relative h-6 w-11 rounded-full transition-colors ${form.enabled ? "bg-primary" : "bg-muted"}`} data-testid="digest-enabled-toggle">
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-[left] ${form.enabled ? "left-[22px]" : "left-0.5"}`} />
          </button>
          <span>{form.enabled ? <span className="flex items-center gap-1.5"><MailCheck size={14} className="text-primary" /> Her hafta gönder</span> : "Kapalı"}</span>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">Gün
          <select value={form.weekday} onChange={(e) => update({ weekday: Number(e.target.value) })} className={selectClass} data-testid="digest-weekday-select">{WEEKDAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select>
        </label>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">Saat
          <select value={form.hour} onChange={(e) => update({ hour: Number(e.target.value) })} className={selectClass} data-testid="digest-hour-select">{Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>)}</select>
        </label>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={() => (preview ? setPreview(null) : loadPreview.mutate())} disabled={loadPreview.isPending} data-testid="digest-preview-button"><Eye size={14} /> {preview ? "Önizlemeyi kapat" : "Önizle"}</Button>
          <Button onClick={() => sendNow.mutate()} disabled={sendNow.isPending} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid="digest-send-now-button"><Send size={14} /> {sendNow.isPending ? "Gönderiliyor…" : "Şimdi gönder"}</Button>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted-foreground" data-testid="digest-status-line">
        {prefs.data?.last_sent_at ? `Son gönderim: ${new Date(prefs.data.last_sent_at).toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" })}` : "Henüz gönderilmedi."} Saatler Türkiye saatidir. Yalnızca gerçekten yararlı içerik gönderilir; e-posta hiçbir zaman şifre veya kart bilgisi istemez.
      </p>
      <div className="mt-5 border-t border-border pt-5" data-testid="reminder-section">
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold"><BellRing size={15} className="text-amber-500" /> Ödeme günü hatırlatması</p>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-sm" data-testid="reminder-enabled-row">
            <button type="button" role="switch" aria-checked={form.reminders_enabled} onClick={() => update({ reminders_enabled: !form.reminders_enabled })} className={`relative h-6 w-11 rounded-full transition-colors ${form.reminders_enabled ? "bg-amber-500" : "bg-muted"}`} data-testid="reminder-enabled-toggle">
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-[left] ${form.reminders_enabled ? "left-[22px]" : "left-0.5"}`} />
            </button>
            <span>{form.reminders_enabled ? "Vade gününün sabahı e-posta gönder" : "Kapalı"}</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">Saat
            <select value={form.reminder_hour} onChange={(e) => update({ reminder_hour: Number(e.target.value) })} className={selectClass} data-testid="reminder-hour-select">{Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>)}</select>
          </label>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" onClick={() => (reminderPreview ? setReminderPreview(null) : loadReminderPreview.mutate())} disabled={loadReminderPreview.isPending} data-testid="reminder-preview-button"><Eye size={14} /> {reminderPreview ? "Önizlemeyi kapat" : "Bugünü önizle"}</Button>
            <Button variant="outline" onClick={() => sendReminder.mutate()} disabled={sendReminder.isPending} className="border-amber-500/40 text-amber-600 hover:bg-amber-500/10 dark:text-amber-400" data-testid="reminder-send-now-button"><Send size={14} /> {sendReminder.isPending ? "Gönderiliyor…" : "Bugünkü hatırlatmayı gönder"}</Button>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted-foreground" data-testid="reminder-status-line">
          Yalnızca o gün vadesi gelen fatura veya abonelik varsa, günde en fazla bir e-posta gönderilir. {prefs.data?.last_reminder_date ? `Son hatırlatma: ${new Date(`${prefs.data.last_reminder_date}T12:00:00`).toLocaleDateString("tr-TR", { dateStyle: "medium" })}.` : "Henüz hatırlatma gönderilmedi."}
        </p>
        {reminderPreview && (
          <div className="mt-4 overflow-hidden rounded-xl border border-border" data-testid="reminder-preview">
            {reminderPreview.due_count === 0 || !reminderPreview.html
              ? <p className="px-4 py-6 text-center text-sm text-muted-foreground" data-testid="reminder-preview-empty">Bugün vadesi gelen ödeme yok — hatırlatma gönderilmez.</p>
              : <>
                  <p className="border-b border-border bg-muted/50 px-4 py-2 text-xs"><span className="text-muted-foreground">Konu:</span> <span data-testid="reminder-preview-subject">{reminderPreview.subject}</span></p>
                  <iframe title="Ödeme günü hatırlatması önizleme" srcDoc={reminderPreview.html} sandbox="" className="h-[26rem] w-full bg-[#f6f5f0]" data-testid="reminder-preview-frame" />
                </>}
          </div>
        )}
      </div>

      {preview && (
        <div className="mt-4 overflow-hidden rounded-xl border border-border" data-testid="digest-preview">
          <p className="border-b border-border bg-muted/50 px-4 py-2 text-xs"><span className="text-muted-foreground">Konu:</span> <span data-testid="digest-preview-subject">{preview.subject}</span></p>
          <iframe title="Haftalık özet önizleme" srcDoc={preview.html} sandbox="" className="h-[36rem] w-full bg-[#f6f5f0]" data-testid="digest-preview-frame" />
        </div>
      )}
    </Panel>
  );
}


function GamingBudgetPanel() {
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
      toast.success("Gaming aylık limitin kaydedildi");
      qc.invalidateQueries({ queryKey: ["gaming"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
    onError: () => toast.error("Kaydedilemedi"),
  });

  const clear = useMutation({
    mutationFn: () => apiDelete<void>("/gaming/budget"),
    onSuccess: () => {
      toast.success("Gaming limiti kaldırıldı");
      qc.invalidateQueries({ queryKey: ["gaming"] });
    },
  });

  const s = status.data;
  const hasLimit = s?.limit != null;

  return (
    <Panel title="🎮 Gaming aylık limit" description="Aşıldığında bütçe, tasarruf ve uyarılar sayfalarına otomatik yansır" testId="settings-gaming-budget">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[180px]">
          <label className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Aylık limit (₺)</label>
          <Input
            type="number"
            min="0"
            step="10"
            value={limit}
            onChange={(e) => setLimit(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder="Örn. 500"
            data-testid="settings-gaming-budget-input"
          />
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => {
              if (typeof limit !== "number" || limit <= 0) {
                toast.error("Geçerli bir limit gir");
                return;
              }
              save.mutate(limit);
            }}
            disabled={save.isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            data-testid="settings-gaming-budget-save"
          >
            <Gamepad2 size={14} /> {hasLimit ? "Güncelle" : "Kaydet"}
          </Button>
          {hasLimit && (
            <Button variant="outline" onClick={() => clear.mutate()} disabled={clear.isPending} data-testid="settings-gaming-budget-clear">
              Kaldır
            </Button>
          )}
        </div>
      </div>
      {s && hasLimit && (
        <div className="mt-4" data-testid="settings-gaming-budget-status">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Bu ay kullanımın</span>
            <span className={`font-mono ${s.exceeded ? "text-rose-500" : s.warning ? "text-amber-500" : "text-foreground"}`}>
              {money(s.spent, "TRY", 0)} / {money(s.limit!, "TRY", 0)} · {percent(s.percent)}
            </span>
          </div>
          <ProgressBar percent={s.percent} exceeded={s.exceeded} />
          <p className="mt-2 text-[11px] text-muted-foreground">
            Kayıt Bütçe ekranına da "Gaming" kategorisi olarak yansır; aşıldığında panel uyarılarına düşer.
          </p>
        </div>
      )}
      {!hasLimit && (
        <p className="mt-3 rounded-lg border border-border bg-muted/30 p-3 text-[11px] text-muted-foreground">
          Henüz Gaming aylık limitin yok. Buraya bir tutar gir; her Gaming satın alman otomatik olarak buraya işlenir ve %85'i geçince ana panelde uyarı görürsün.
        </p>
      )}
    </Panel>
  );
}
