import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, ArrowLeft, Bell, BellRing, CheckCircle2, Coins, ExternalLink, ShieldCheck, Timer, Trash2, Wallet2 } from "lucide-react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { money } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { GamingOffer, GamingProductDetail, GamingPurchasePayload, GamingPurchaseResponse, GamingWatch, GamingWatchPayload } from "@/lib/types";
import { PageHeader, Panel } from "@/components/shared/ui-bits";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

function reliabilityColor(rel: string) {
  return rel === "verified"
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
    : rel === "trusted"
      ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-500"
      : "border-amber-500/30 bg-amber-500/10 text-amber-500";
}

export default function GamingProduct() {
  const { t } = useT();
  const reliabilityLabel = (rel: string) => rel === "verified" ? t("gaming.reliability.verified") : rel === "trusted" ? t("gaming.reliability.trusted") : t("gaming.reliability.caution");
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const [pendingOffer, setPendingOffer] = useState<GamingOffer | null>(null);
  const [watchModal, setWatchModal] = useState(false);
  const [targetPrice, setTargetPrice] = useState<number | "">("");

  const detail = useQuery({
    queryKey: ["gaming", "product", id],
    queryFn: () => apiGet<GamingProductDetail>(`/gaming/products/${id}`),
    enabled: Boolean(id),
    staleTime: 60_000,
  });

  const watches = useQuery({
    queryKey: ["gaming", "watches"],
    queryFn: () => apiGet<GamingWatch[]>("/gaming/watches"),
    staleTime: 30_000,
  });

  const existingWatch = useMemo(() => (watches.data ?? []).find((w) => w.product_id === id) ?? null, [watches.data, id]);

  const record = useMutation({
    mutationFn: (payload: GamingPurchasePayload) => apiPost<GamingPurchaseResponse>("/gaming/purchases", payload),
    onSuccess: (data) => {
      toast.success(t("gamingProduct.toast.purchaseRecorded", { amount: money(data.purchase.amount_try, "TRY", 2) }));
      setPendingOffer(null);
      qc.invalidateQueries({ queryKey: ["gaming", "summary"] });
      qc.invalidateQueries({ queryKey: ["expenses"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error(t("gamingProduct.toast.purchaseFailed")),
  });

  const createWatch = useMutation({
    mutationFn: (payload: GamingWatchPayload) => apiPost<GamingWatch>("/gaming/watches", payload),
    onSuccess: () => {
      toast.success(t("gamingProduct.toast.watchAdded"));
      setWatchModal(false);
      qc.invalidateQueries({ queryKey: ["gaming", "watches"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
    onError: () => toast.error(t("gamingProduct.toast.watchFailed")),
  });

  const removeWatch = useMutation({
    mutationFn: (watchId: string) => apiDelete<void>(`/gaming/watches/${watchId}`),
    onSuccess: () => {
      toast.success(t("gamingProduct.toast.watchRemoved"));
      qc.invalidateQueries({ queryKey: ["gaming", "watches"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const offers = detail.data?.offers ?? [];
  const best = offers[0] ?? null;
  const savingsVsWorst = useMemo(() => {
    if (offers.length < 2) return 0;
    return offers[offers.length - 1].price_try - offers[0].price_try;
  }, [offers]);

  if (detail.isLoading) return <div className="grid min-h-[50svh] place-items-center text-sm text-muted-foreground" data-testid="gaming-product-loading">{t("gamingProduct.loading")}</div>;
  if (detail.error || !detail.data) return <div className="grid min-h-[50svh] place-items-center text-sm text-rose-500" data-testid="gaming-product-error">{t("gamingProduct.notFound")}</div>;
  const p = detail.data;

  function openOffer(offer: GamingOffer) {
    window.open(offer.url, "_blank", "noopener,noreferrer");
    setPendingOffer(offer);
  }

  function confirmPurchase() {
    if (!pendingOffer) return;
    record.mutate({
      offer_id: pendingOffer.id,
      product_id: p.id,
      seller_id: pendingOffer.seller_id,
      amount_try: pendingOffer.price_try,
    });
  }

  return (
    <div className="space-y-6" data-testid="gaming-product-page">
      <Link to={`/gaming/games/${p.game_slug}`} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-testid="gaming-product-back">
        <ArrowLeft size={13} /> {p.game_name}
      </Link>

      <PageHeader
        eyebrow={`${p.game_name} · ${p.game_currency}`}
        title={p.name}
        description={t("gamingProduct.description", { count: p.offer_count })}
        testId="gaming-product-header"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {existingWatch ? (
              <Button variant="outline" size="sm" onClick={() => removeWatch.mutate(existingWatch.id)} disabled={removeWatch.isPending} data-testid="gaming-watch-remove">
                <BellRing size={13} /> {t("gamingProduct.removeWatch", { price: existingWatch.target_price_try.toFixed(0) })}
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={() => { setTargetPrice(best ? Math.floor(best.price_try * 0.95) : ""); setWatchModal(true); }} data-testid="gaming-watch-add">
                <Bell size={13} /> {t("gamingProduct.trackPrice")}
              </Button>
            )}
            {best ? (
              <div className="rounded-xl border border-primary/30 bg-primary/10 px-4 py-2 text-right" data-testid="gaming-product-best">
                <p className="text-[10px] uppercase tracking-wider text-primary">{t("gamingProduct.best")}</p>
                <p className="font-mono text-lg font-bold text-foreground">{money(best.price_try, "TRY", 2)}</p>
                <p className="text-[11px] text-muted-foreground">{best.seller_name} · {best.delivery}</p>
              </div>
            ) : null}
          </div>
        }
      />

      {existingWatch && (
        <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs text-emerald-500" data-testid="gaming-existing-watch">
          <span className="inline-flex items-center gap-2">
            <Bell size={13} /> {t("gamingProduct.watchingAt")} <span className="font-mono font-semibold">{money(existingWatch.target_price_try, "TRY", 2)}</span>
            {existingWatch.triggered && <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 font-semibold">{t("gamingProduct.targetHit")}</span>}
          </span>
          <Button variant="ghost" size="sm" onClick={() => removeWatch.mutate(existingWatch.id)} className="text-emerald-500 hover:text-rose-500" aria-label={t("common.remove")} data-testid="gaming-existing-watch-remove">
            <Trash2 size={12} />
          </Button>
        </div>
      )}

      {savingsVsWorst > 0 && (
        <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2 text-xs text-emerald-500" data-testid="gaming-savings-hint">
          {t("gamingProduct.savingsHint", { amount: money(savingsVsWorst, "TRY", 2) })}
        </div>
      )}

      <Panel title={t("gamingProduct.offersTitle")} description={t("gamingProduct.offersDescription")} testId="gaming-offers-panel">
        <ul className="divide-y divide-border" data-testid="gaming-offers-list">
          {offers.map((offer, idx) => (
            <li key={offer.id} className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center" data-testid={`gaming-offer-${offer.id}`}>
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg text-[11px] font-mono font-semibold ${idx === 0 ? "bg-primary/12 text-primary" : "bg-muted text-muted-foreground"}`}>
                  {idx + 1}.
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-semibold text-foreground" data-testid={`gaming-offer-seller-${offer.id}`}>{offer.seller_name}</p>
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${reliabilityColor(offer.seller_reliability)}`}>
                      <ShieldCheck size={10} /> {reliabilityLabel(offer.seller_reliability)}
                    </span>
                  </div>
                  <p className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                    <Timer size={11} /> {offer.delivery}
                    <span className="text-border">·</span>
                    <span className="truncate">{offer.seller_domain}</span>
                    {offer.has_override && <span className="rounded-full border border-primary/25 bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary" data-testid={`gaming-offer-override-${offer.id}`}>{t("gamingProduct.edited")}</span>}
                    {offer.campaign && <span className="rounded-full border border-fuchsia-500/25 bg-fuchsia-500/10 px-1.5 py-0.5 text-[9px] font-medium text-fuchsia-400">{offer.campaign}</span>}
                    {offer.estimated_commission_try > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-500" data-testid={`gaming-offer-commission-${offer.id}`}>
                        <Coins size={9} /> {t("gamingProduct.earnings", { amount: money(offer.estimated_commission_try, "TRY", 2) })}
                      </span>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4 sm:justify-end">
                <div className="text-right">
                  <p className="font-mono text-base font-bold text-foreground" data-testid={`gaming-offer-price-${offer.id}`}>{money(offer.price_try, "TRY", 2)}</p>
                  {offer.original_price_try && offer.original_price_try > offer.price_try && (
                    <p className="text-[11px] text-muted-foreground line-through">{money(offer.original_price_try, "TRY", 2)}</p>
                  )}
                </div>
                <Button size="sm" onClick={() => openOffer(offer)} className={idx === 0 ? "bg-primary text-primary-foreground hover:bg-primary/90" : ""} variant={idx === 0 ? "default" : "outline"} data-testid={`gaming-buy-${offer.id}`}>
                  <ExternalLink size={13} /> {t("gamingProduct.buy")}
                </Button>
              </div>
            </li>
          ))}
          {offers.length === 0 && <li className="py-6 text-center text-sm text-muted-foreground">{t("gamingProduct.noOffers")}</li>}
        </ul>

        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-[11px] leading-relaxed text-amber-500" data-testid="gaming-safety-note">
          <p className="flex items-start gap-2"><AlertTriangle size={13} className="mt-0.5 shrink-0" /> {t("gamingProduct.safetyNote")}</p>
        </div>
      </Panel>

      <Dialog open={watchModal} onOpenChange={(next) => !next && !createWatch.isPending && setWatchModal(false)}>
        <DialogContent className="border-border bg-card sm:max-w-md" data-testid="gaming-watch-modal">
          <DialogHeader>
            <p className="text-[11px] uppercase tracking-wider text-primary">{t("gamingProduct.watchModal.eyebrow")}</p>
            <DialogTitle className="font-heading text-lg font-bold">{t("gamingProduct.watchModal.title")}</DialogTitle>
            <DialogDescription>{t("gamingProduct.watchModal.description", { price: best ? money(best.price_try, "TRY", 2) : "-" })}</DialogDescription>
          </DialogHeader>
          <div>
            <label className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground" htmlFor="gaming-watch-target-input">{t("gamingProduct.watchModal.field")}</label>
            <Input
              id="gaming-watch-target-input"
              type="number"
              step="0.01"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value === "" ? "" : Number(e.target.value))}
              placeholder={best ? String(Math.floor(best.price_try * 0.95)) : "0"}
              data-testid="gaming-watch-target-input"
            />
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variant="outline" onClick={() => setWatchModal(false)} disabled={createWatch.isPending} className="flex-1" data-testid="gaming-watch-cancel">
              {t("common.cancel")}
            </Button>
            <Button
              onClick={() => {
                if (typeof targetPrice !== "number" || targetPrice <= 0) {
                  toast.error(t("gamingProduct.watchModal.invalid"));
                  return;
                }
                createWatch.mutate({ product_id: id, target_price_try: Number(targetPrice), notify_email: true, notify_in_app: true, note: "" });
              }}
              disabled={createWatch.isPending}
              className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90"
              data-testid="gaming-watch-confirm"
            >
              <Bell size={14} /> {t("gamingProduct.watchModal.confirm")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(pendingOffer)} onOpenChange={(next) => !next && !record.isPending && setPendingOffer(null)}>
        <DialogContent className="border-border bg-card sm:max-w-md" data-testid="gaming-confirm-modal">
          <DialogHeader>
            <p className="text-[11px] uppercase tracking-wider text-primary">{t("gamingProduct.confirmModal.eyebrow")}</p>
            <DialogTitle className="font-heading text-lg font-bold" data-testid="gaming-confirm-title">{p.game_name} · {p.name}</DialogTitle>
            {pendingOffer && <DialogDescription>{t("gamingProduct.confirmModal.description", { seller: pendingOffer.seller_name })}</DialogDescription>}
          </DialogHeader>
          <div className="flex items-baseline justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("gamingProduct.confirmModal.amount")}</p>
            <p className="font-mono text-xl font-bold text-foreground" data-testid="gaming-confirm-amount">{pendingOffer ? money(pendingOffer.price_try, "TRY", 2) : "-"}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variant="outline" onClick={() => setPendingOffer(null)} disabled={record.isPending} className="flex-1" data-testid="gaming-confirm-cancel">
              {t("gamingProduct.confirmModal.notYet")}
            </Button>
            <Button onClick={confirmPurchase} disabled={record.isPending} className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90" data-testid="gaming-confirm-buy">
              <CheckCircle2 size={14} /> {t("gamingProduct.confirmModal.bought")}
            </Button>
          </div>
          <p className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
            <Wallet2 size={11} /> {t("gamingProduct.confirmModal.paymentNote")}
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}
