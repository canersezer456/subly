import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Check, Clock, Download, Filter, History, PencilLine, RotateCcw, Save, Undo2, Upload, X } from "lucide-react";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { money } from "@/lib/format";
import type { GamingBulkImport, GamingCatalogAdminRow, GamingCatalogHistoryEntry, GamingImportResult, GamingOfferOverrideInput } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, Panel } from "@/components/shared/ui-bits";

function reliabilityChipColor(rel: string) {
  return rel === "verified"
    ? "text-emerald-500"
    : rel === "trusted"
      ? "text-cyan-500"
      : "text-amber-500";
}

export default function GamingAdmin() {
  const qc = useQueryClient();
  const [gameFilter, setGameFilter] = useState<string>("all");
  const [onlyOverrides, setOnlyOverrides] = useState(false);
  const [editing, setEditing] = useState<Record<string, GamingOfferOverrideInput>>({});
  const [importJson, setImportJson] = useState("");
  const [historyOffer, setHistoryOffer] = useState<GamingCatalogAdminRow | null>(null);
  const csvInput = useRef<HTMLInputElement>(null);
  const rows = useQuery({ queryKey: ["gaming", "admin"], queryFn: () => apiGet<GamingCatalogAdminRow[]>("/gaming/admin/catalog"), staleTime: 15_000 });
  const history = useQuery({
    queryKey: ["gaming", "admin-history", historyOffer?.offer_id],
    queryFn: () => apiGet<GamingCatalogHistoryEntry[]>(`/gaming/admin/catalog/history?offer_id=${historyOffer?.offer_id}`),
    enabled: !!historyOffer,
    staleTime: 5_000,
  });

  const save = useMutation({
    mutationFn: ({ offer_id, payload }: { offer_id: string; payload: GamingOfferOverrideInput }) =>
      apiPut<GamingCatalogAdminRow>(`/gaming/admin/catalog/${offer_id}`, payload),
    onSuccess: (_data, vars) => {
      toast.success("Fiyat güncellendi");
      setEditing((prev) => {
        const next = { ...prev };
        delete next[vars.offer_id];
        return next;
      });
      qc.invalidateQueries({ queryKey: ["gaming"] });
    },
    onError: () => toast.error("Kayıt yapılamadı"),
  });

  const clear = useMutation({
    mutationFn: (offer_id: string) => apiDelete<void>(`/gaming/admin/catalog/${offer_id}`),
    onSuccess: () => {
      toast.success("Özel fiyat kaldırıldı");
      qc.invalidateQueries({ queryKey: ["gaming"] });
    },
  });

  const revert = useMutation({
    mutationFn: (history_id: string) => apiPost<GamingCatalogAdminRow>(`/gaming/admin/catalog/history/${history_id}/revert`),
    onSuccess: () => {
      toast.success("Önceki değere geri alındı");
      qc.invalidateQueries({ queryKey: ["gaming"] });
      qc.invalidateQueries({ queryKey: ["gaming", "admin-history"] });
    },
    onError: () => toast.error("Geri alma başarısız"),
  });

  const resetAll = useMutation({
    mutationFn: () => apiPost<void>("/gaming/admin/catalog/reset"),
    onSuccess: () => {
      toast.success("Tüm özel fiyatlar sıfırlandı");
      qc.invalidateQueries({ queryKey: ["gaming"] });
    },
  });

  const importJsonMut = useMutation({
    mutationFn: (payload: GamingBulkImport) => apiPost<GamingImportResult>("/gaming/admin/catalog/import", payload),
    onSuccess: (data) => {
      toast.success(`${data.applied} teklif güncellendi · ${data.skipped} atlandı`);
      setImportJson("");
      qc.invalidateQueries({ queryKey: ["gaming"] });
    },
    onError: () => toast.error("JSON içeriği okunamadı"),
  });

  const uploadCsv = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/gaming/admin/catalog/import/csv", { method: "POST", credentials: "include", body: fd });
      if (!res.ok) throw new Error(await res.text());
      return (await res.json()) as GamingImportResult;
    },
    onSuccess: (data) => {
      toast.success(`${data.applied} satır uygulandı · ${data.skipped} atlandı`);
      qc.invalidateQueries({ queryKey: ["gaming"] });
      if (csvInput.current) csvInput.current.value = "";
    },
    onError: () => toast.error("CSV yüklenemedi"),
  });

  const gameOptions = useMemo(() => {
    const set = new Set<string>();
    (rows.data ?? []).forEach((r) => set.add(r.game_slug));
    return Array.from(set);
  }, [rows.data]);

  const filteredRows = useMemo(() => {
    let list = rows.data ?? [];
    if (gameFilter !== "all") list = list.filter((r) => r.game_slug === gameFilter);
    if (onlyOverrides) list = list.filter((r) => r.has_override);
    return list;
  }, [rows.data, gameFilter, onlyOverrides]);

  function stageEdit(offer_id: string, patch: GamingOfferOverrideInput) {
    setEditing((prev) => ({ ...prev, [offer_id]: { ...prev[offer_id], ...patch } }));
  }

  function commit(row: GamingCatalogAdminRow) {
    const payload = editing[row.offer_id];
    if (!payload || Object.keys(payload).length === 0) return;
    save.mutate({ offer_id: row.offer_id, payload });
  }

  function exportJson() {
    const list = (rows.data ?? []).filter((r) => r.has_override).map((r) => ({
      offer_id: r.offer_id,
      price_try: r.current_price_try,
      original_price_try: r.current_original_price_try,
      delivery: r.current_delivery,
      campaign: r.current_campaign,
      url: r.current_url,
    }));
    const blob = new Blob([JSON.stringify({ overrides: list }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `subly-gaming-overrides-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function importFromJson() {
    try {
      const parsed = JSON.parse(importJson);
      const overrides = Array.isArray(parsed) ? parsed : parsed.overrides;
      if (!Array.isArray(overrides)) throw new Error("bad shape");
      importJsonMut.mutate({ overrides });
    } catch {
      toast.error("Geçerli JSON değil");
    }
  }

  return (
    <div className="space-y-6" data-testid="gaming-admin-page">
      <Link to="/gaming" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-testid="gaming-admin-back">
        <ArrowLeft size={13} /> Gaming ana sayfası
      </Link>

      <PageHeader
        eyebrow="Katalog Editörü"
        title="Fiyatları sen yönet"
        description="Gerçek zamanlı gördüğün fiyatları buradan güncelle. Değişikliklerin yalnızca senin hesabında geçerlidir. JSON/CSV yükleyip toplu güncelleme yapabilirsin."
        testId="gaming-admin-header"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={exportJson} data-testid="gaming-admin-export">
              <Download size={13} /> JSON dışa aktar
            </Button>
            <Button variant="outline" onClick={() => csvInput.current?.click()} data-testid="gaming-admin-csv-btn">
              <Upload size={13} /> CSV yükle
            </Button>
            <input
              ref={csvInput}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadCsv.mutate(f);
              }}
              data-testid="gaming-admin-csv-input"
            />
            <Button variant="outline" onClick={() => resetAll.mutate()} disabled={resetAll.isPending} data-testid="gaming-admin-reset">
              <RotateCcw size={13} /> Tümünü sıfırla
            </Button>
          </div>
        }
      />

      <Panel title="Toplu JSON içe aktarma" description="Aşağıya paste'le: { overrides: [{ offer_id, price_try, ... }] }" testId="gaming-admin-json-panel">
        <textarea
          value={importJson}
          onChange={(e) => setImportJson(e.target.value)}
          rows={5}
          className="w-full rounded-lg border border-input bg-card p-3 font-mono text-xs"
          placeholder='{"overrides":[{"offer_id":"off-prod-valorant-2050-vp-bynogame","price_try":439}]}'
          data-testid="gaming-admin-json-input"
        />
        <div className="mt-3 flex justify-end">
          <Button onClick={importFromJson} disabled={importJsonMut.isPending || !importJson.trim()} data-testid="gaming-admin-json-apply">
            <Upload size={13} /> Uygula
          </Button>
        </div>
      </Panel>

      <Panel testId="gaming-admin-filter-panel">
        <div className="flex flex-wrap items-center gap-2">
          <Filter size={14} className="text-muted-foreground" />
          <select
            value={gameFilter}
            onChange={(e) => setGameFilter(e.target.value)}
            className="h-9 rounded-lg border border-input bg-card px-3 text-sm"
            data-testid="gaming-admin-filter-game"
          >
            <option value="all">Tüm oyunlar</option>
            {gameOptions.map((slug) => {
              const label = rows.data?.find((r) => r.game_slug === slug)?.game_name ?? slug;
              return <option key={slug} value={slug}>{label}</option>;
            })}
          </select>
          <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={onlyOverrides}
              onChange={(e) => setOnlyOverrides(e.target.checked)}
              className="h-3.5 w-3.5"
              data-testid="gaming-admin-filter-overrides"
            />
            Sadece düzenlenmiş satırlar
          </label>
          <p className="ml-auto text-xs text-muted-foreground" data-testid="gaming-admin-count">{filteredRows.length} satır</p>
        </div>
      </Panel>

      <Panel testId="gaming-admin-table">
        {rows.isLoading ? (
          <p className="py-8 text-center text-sm text-muted-foreground" data-testid="gaming-admin-loading">Yükleniyor…</p>
        ) : filteredRows.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Bu filtreye uyan satır yok.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                  <th className="py-2 pr-2">Ürün / Satıcı</th>
                  <th className="px-2 text-right">Baz Fiyat</th>
                  <th className="px-2 text-right">Fiyat (₺)</th>
                  <th className="px-2">Teslimat</th>
                  <th className="px-2">Kampanya</th>
                  <th className="px-2">Durum</th>
                  <th className="py-2 pl-2 text-right">İşlem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredRows.map((row) => {
                  const draft = editing[row.offer_id];
                  const dirty = draft && Object.keys(draft).length > 0;
                  return (
                    <tr key={row.offer_id} className="align-middle" data-testid={`gaming-admin-row-${row.offer_id}`}>
                      <td className="py-2 pr-2">
                        <p className="font-medium text-foreground">{row.game_name} · {row.product_name}</p>
                        <p className={`text-[11px] ${reliabilityChipColor(row.seller_reliability)}`}>{row.seller_name}</p>
                      </td>
                      <td className="px-2 text-right font-mono text-xs text-muted-foreground">{money(row.base_price_try, "TRY", 2)}</td>
                      <td className="px-2 text-right">
                        <Input
                          type="number"
                          step="0.01"
                          value={draft?.price_try ?? row.current_price_try}
                          onChange={(e) => stageEdit(row.offer_id, { price_try: e.target.value === "" ? undefined : Number(e.target.value) })}
                          className="ml-auto h-8 w-24 text-right font-mono"
                          data-testid={`gaming-admin-price-${row.offer_id}`}
                        />
                      </td>
                      <td className="px-2">
                        <Input
                          value={draft?.delivery ?? row.current_delivery}
                          onChange={(e) => stageEdit(row.offer_id, { delivery: e.target.value })}
                          className="h-8 w-24 text-xs"
                          data-testid={`gaming-admin-delivery-${row.offer_id}`}
                        />
                      </td>
                      <td className="px-2">
                        <Input
                          value={draft?.campaign ?? row.current_campaign ?? ""}
                          onChange={(e) => stageEdit(row.offer_id, { campaign: e.target.value || null })}
                          className="h-8 w-32 text-xs"
                          placeholder="—"
                          data-testid={`gaming-admin-campaign-${row.offer_id}`}
                        />
                      </td>
                      <td className="px-2 text-xs">
                        {row.has_override ? (
                          <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                            <Check size={10} /> Düzenlendi
                          </span>
                        ) : (
                          <span className="text-muted-foreground">Katalog</span>
                        )}
                      </td>
                      <td className="py-2 pl-2 text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm"
                            variant={dirty ? "default" : "outline"}
                            onClick={() => commit(row)}
                            disabled={!dirty || save.isPending}
                            className={dirty ? "bg-primary text-primary-foreground" : ""}
                            data-testid={`gaming-admin-save-${row.offer_id}`}
                          >
                            <Save size={12} />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setHistoryOffer(row)}
                            className="text-muted-foreground hover:text-primary"
                            data-testid={`gaming-admin-history-${row.offer_id}`}
                          >
                            <History size={12} />
                          </Button>
                          {row.has_override && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => clear.mutate(row.offer_id)}
                              className="text-muted-foreground hover:text-rose-500"
                              data-testid={`gaming-admin-clear-${row.offer_id}`}
                            >
                              <X size={12} />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-4 flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-3 text-[11px] leading-relaxed text-muted-foreground" data-testid="gaming-admin-note">
          <PencilLine size={12} className="mt-0.5 shrink-0" />
          Değişikliklerin yalnızca senin hesabındaki Gaming sayfalarını etkiler. offer_id sabit kalır; bu kimliği JSON/CSV içe aktarmalarında referans olarak kullanabilirsin.
        </p>
      </Panel>

      {historyOffer && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/70 px-4" data-testid="gaming-admin-history-modal" onClick={() => setHistoryOffer(null)}>
          <div className="w-full max-w-2xl rounded-2xl border border-border bg-card p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-primary">Geçmiş</p>
                <h2 className="font-heading text-lg font-bold" data-testid="gaming-admin-history-title">
                  {historyOffer.game_name} · {historyOffer.product_name}
                </h2>
                <p className="mt-0.5 text-xs text-muted-foreground">{historyOffer.seller_name}</p>
              </div>
              <button type="button" onClick={() => setHistoryOffer(null)} className="text-muted-foreground hover:text-foreground" data-testid="gaming-admin-history-close">
                <X size={16} />
              </button>
            </div>

            <div className="mt-4 max-h-[24rem] overflow-y-auto">
              {history.isLoading ? (
                <p className="py-8 text-center text-xs text-muted-foreground" data-testid="gaming-admin-history-loading">Yükleniyor…</p>
              ) : (history.data ?? []).length === 0 ? (
                <p className="py-8 text-center text-xs text-muted-foreground" data-testid="gaming-admin-history-empty">Bu ürün için henüz düzenleme yok.</p>
              ) : (
                <ul className="space-y-2" data-testid="gaming-admin-history-list">
                  {history.data!.map((entry) => (
                    <li key={entry.id} className="rounded-xl border border-border bg-muted/30 p-3" data-testid={`gaming-admin-history-entry-${entry.id}`}>
                      <div className="mb-2 flex items-center justify-between gap-2 text-[11px]">
                        <span className="inline-flex items-center gap-1 rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 font-medium text-primary">
                          <Clock size={10} /> {new Date(entry.changed_at).toLocaleString("tr-TR")}
                        </span>
                        <span className="text-muted-foreground uppercase tracking-wider">{entry.action}</span>
                      </div>
                      <div className="grid gap-2 text-xs sm:grid-cols-2">
                        <div>
                          <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Önce</p>
                          <pre className="max-h-24 overflow-y-auto rounded bg-background/50 p-2 font-mono text-[11px]">
                            {entry.before ? JSON.stringify(entry.before, null, 2) : "— katalog varsayılan —"}
                          </pre>
                        </div>
                        <div>
                          <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Sonra</p>
                          <pre className="max-h-24 overflow-y-auto rounded bg-background/50 p-2 font-mono text-[11px]">
                            {entry.after ? JSON.stringify(entry.after, null, 2) : "— katalog varsayılan —"}
                          </pre>
                        </div>
                      </div>
                      <div className="mt-3 flex justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => revert.mutate(entry.id)}
                          disabled={revert.isPending}
                          data-testid={`gaming-admin-history-revert-${entry.id}`}
                        >
                          <Undo2 size={12} /> Bu değere geri al
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
