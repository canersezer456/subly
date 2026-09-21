import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BadgeCheck, Bell, Coins, Flame, Gift, LineChart, Search, Settings2, ShieldCheck, Sparkles, Tag, Timer, Wallet2, Zap } from "lucide-react";
import { apiGet } from "@/lib/api";
import { money, monthIso, percent } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { GamingBudgetStatus, GamingDeal, GamingEarningsSummary, GamingGame, GamingHome, GamingSearchResponse, GamingSummary, GamingWatch } from "@/lib/types";
import { PageHeader, Panel, ProgressBar } from "@/components/shared/ui-bits";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type Section = "popular" | "cheapest" | "campaigns" | "instant";

const SECTIONS: { key: Section; label: string; icon: typeof Flame; hint: string }[] = [
  { key: "popular", label: "🔥 Popüler", icon: Flame, hint: "Türkiye'de en çok aranan başlıklar" },
  { key: "cheapest", label: "💰 En Ucuz Fırsatlar", icon: Tag, hint: "Onaylı satıcılardan en düşük fiyat" },
  { key: "campaigns", label: "🎁 Kampanyalar", icon: Gift, hint: "İndirim ve kupon avantajlı ürünler" },
  { key: "instant", label: "⚡ Anında Teslimat", icon: Zap, hint: "Sipariş sonrası saniyeler içinde teslim" },
];

function reliabilityLabel(rel: string) {
  return rel === "verified" ? "Onaylı" : rel === "trusted" ? "Güvenilir" : "Dikkat";
}

function reliabilityColor(rel: string) {
  return rel === "verified"
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
    : rel === "trusted"
      ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-500"
      : "border-amber-500/30 bg-amber-500/10 text-amber-500";
}

function DealCard({ deal, testId }: { deal: GamingDeal; testId: string }) {
  return (
    <Link
      to={`/gaming/products/${deal.product_id}`}
      className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-[border-color,transform] hover:-translate-y-0.5 hover:border-primary/40"
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: deal.accent_color }}>
            {deal.game_name}
          </p>
          <p className="mt-1 font-heading text-sm font-semibold text-foreground">{deal.product_name}</p>
        </div>
        <ArrowUpRight size={14} className="text-muted-foreground/60 transition-colors group-hover:text-primary" />
      </div>
      <div className="flex items-end justify-between gap-2">
        <div>
          <p className="font-mono text-xl font-bold text-foreground" data-testid={`${testId}-price`}>{money(deal.price_try, "TRY", 2)}</p>
          {deal.original_price_try && deal.original_price_try > deal.price_try && (
            <p className="text-[11px] text-muted-foreground line-through">{money(deal.original_price_try, "TRY", 2)}</p>
          )}
        </div>
        {deal.discount_percent > 0 && (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-500">-%{deal.discount_percent}</span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium ${reliabilityColor(deal.seller_reliability)}`}>
          <ShieldCheck size={10} /> {deal.seller_name}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/60 px-2 py-0.5 text-muted-foreground">
          <Timer size={10} /> {deal.delivery}
        </span>
        {deal.campaign && (
          <span className="inline-flex items-center gap-1 rounded-full border border-fuchsia-500/30 bg-fuchsia-500/10 px-2 py-0.5 text-fuchsia-400">
            <Gift size={10} /> {deal.campaign}
          </span>
        )}
      </div>
    </Link>
  );
}

function GameTile({ game, testId }: { game: GamingGame; testId: string }) {
  return (
    <Link
      to={`/gaming/games/${game.slug}`}
      className="group flex items-center gap-3 rounded-xl border border-border bg-card p-3 transition-[border-color,transform] hover:-translate-y-0.5 hover:border-primary/40"
      data-testid={testId}
    >
      <span
        className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl"
        style={{ backgroundColor: `${game.accent_color}22`, color: game.accent_color }}
      >
        <img src={game.icon_url} alt="" className="h-8 w-8 object-contain" loading="lazy" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-foreground">{game.name}</p>
        <p className="truncate text-[11px] text-muted-foreground">
          {game.currency} · {game.product_count} ürün
        </p>
      </div>
      <div className="text-right">
        {game.best_price_try != null && (
          <p className="font-mono text-xs font-semibold text-foreground" data-testid={`${testId}-price`}>{money(game.best_price_try, "TRY", 0)}</p>
        )}
        <p className="text-[10px] text-muted-foreground">başlangıç</p>
      </div>
    </Link>
  );
}

export default function Gaming() {
  const [q, setQ] = useState("");
  const [section, setSection] = useState<Section>("popular");
  const { t } = useT();
  const home = useQuery({ queryKey: ["gaming", "home"], queryFn: () => apiGet<GamingHome>("/gaming/home"), staleTime: 60_000 });
  const summary = useQuery({ queryKey: ["gaming", "summary", monthIso()], queryFn: () => apiGet<GamingSummary>(`/gaming/summary?month=${monthIso()}`), staleTime: 30_000 });
  const budget = useQuery({ queryKey: ["gaming", "budget", monthIso()], queryFn: () => apiGet<GamingBudgetStatus>(`/gaming/budget?month=${monthIso()}`), staleTime: 30_000 });
  const earnings = useQuery({ queryKey: ["gaming", "earnings", monthIso()], queryFn: () => apiGet<GamingEarningsSummary>(`/gaming/earnings?month=${monthIso()}`), staleTime: 30_000 });
  const watches = useQuery({ queryKey: ["gaming", "watches"], queryFn: () => apiGet<GamingWatch[]>("/gaming/watches"), staleTime: 30_000 });
  const search = useQuery({
    queryKey: ["gaming", "search", q],
    queryFn: () => apiGet<GamingSearchResponse>(`/gaming/search?q=${encodeURIComponent(q.trim())}`),
    enabled: q.trim().length >= 2,
    staleTime: 15_000,
  });

  const sectionDeals: GamingDeal[] = useMemo(() => {
    if (!home.data) return [];
    if (section === "cheapest") return home.data.cheapest_offers;
    if (section === "campaigns") return home.data.campaigns;
    if (section === "instant") return home.data.instant_delivery;
    // popular -> take first cheapest offer per popular game
    const popularSlugs = new Set(home.data.popular_games.map((g) => g.slug));
    const seen = new Set<string>();
    const list: GamingDeal[] = [];
    for (const deal of home.data.cheapest_offers) {
      if (!popularSlugs.has(deal.game_slug)) continue;
      if (seen.has(deal.product_id)) continue;
      seen.add(deal.product_id);
      list.push(deal);
    }
    return list;
  }, [home.data, section]);

  if (home.isLoading) {
    return <div className="grid min-h-[60svh] place-items-center text-sm text-muted-foreground" data-testid="gaming-loading">Gaming kataloğu yükleniyor…</div>;
  }
  if (home.error || !home.data) {
    return <div className="grid min-h-[60svh] place-items-center text-sm text-rose-500" data-testid="gaming-error">Gaming kataloğu şu an açılamıyor.</div>;
  }
  const data = home.data;
  const monthlyTotal = summary.data?.total ?? 0;
  const monthlyCount = summary.data?.count ?? 0;

  return (
    <div className="space-y-8" data-testid="gaming-page">
      <PageHeader
        eyebrow={t("gaming.eyebrow")}
        title={t("gaming.title")}
        description={t("gaming.description")}
        testId="gaming-header"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-500" data-testid="gaming-updated">
              <BadgeCheck size={12} /> {t("gaming.catalog.updated", { date: new Date(data.updated_at).toLocaleDateString(undefined, { day: "numeric", month: "long" }) })}
            </div>
            <Button render={<Link to="/gaming/kazanc" />} variant="outline" size="sm" data-testid="gaming-earnings-link">
              <LineChart size={13} /> {t("gaming.earnings.button")}
            </Button>
            <Button render={<Link to="/gaming/admin" />} variant="outline" size="sm" data-testid="gaming-admin-link">
              <Settings2 size={13} /> {t("gaming.catalog.button")}
            </Button>
          </div>
        }
      />

      <Panel testId="gaming-search-panel">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Oyun veya ürün ara (örn. Valorant, 2105 RP, PSN)"
            className="h-12 pl-9 text-sm"
            data-testid="gaming-search-input"
          />
        </div>
        {q.trim().length >= 2 && (
          <div className="mt-4 grid gap-3 md:grid-cols-2" data-testid="gaming-search-results">
            <div>
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Oyunlar</p>
              <div className="space-y-1.5">
                {(search.data?.games ?? []).slice(0, 5).map((g) => (
                  <GameTile key={g.slug} game={g} testId={`gaming-search-game-${g.slug}`} />
                ))}
                {(search.data?.games?.length ?? 0) === 0 && <p className="text-xs text-muted-foreground">Eşleşen oyun yok.</p>}
              </div>
            </div>
            <div>
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Ürünler</p>
              <div className="space-y-1.5">
                {(search.data?.products ?? []).slice(0, 6).map((p) => (
                  <Link
                    key={p.id}
                    to={`/gaming/products/${p.id}`}
                    className="flex items-center justify-between rounded-lg border border-border bg-card px-3 py-2 text-sm hover:border-primary/40"
                    data-testid={`gaming-search-product-${p.id}`}
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-medium">{p.name}</span>
                      <span className="block text-[11px] text-muted-foreground">{p.game_name}</span>
                    </span>
                    {p.best_price_try != null && <span className="font-mono text-xs font-semibold">{money(p.best_price_try, "TRY", 0)}</span>}
                  </Link>
                ))}
                {(search.data?.products?.length ?? 0) === 0 && <p className="text-xs text-muted-foreground">Eşleşen ürün yok.</p>}
              </div>
            </div>
          </div>
        )}
      </Panel>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Bugünün Gaming Fırsatları" description="Kampanyalı ve düşük fiyatlı öne çıkan seçim" testId="gaming-today-deals">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.today_deals.map((d) => (
              <DealCard key={d.offer_id} deal={d} testId={`gaming-today-deal-${d.offer_id}`} />
            ))}
          </div>
        </Panel>
        <Panel title="Bu ay Gaming harcaman" description="Otomatik olarak gider dashboarduna işlenir" testId="gaming-monthly-panel">
          <div className="flex items-baseline gap-2">
            <Sparkles size={16} className="text-primary" />
            <p className="font-mono text-3xl font-bold text-foreground" data-testid="gaming-monthly-total">{money(monthlyTotal, "TRY", 2)}</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground" data-testid="gaming-monthly-count">{monthlyCount} satın alma</p>
          {budget.data?.limit != null && (
            <div className="mt-4" data-testid="gaming-budget-progress">
              <div className="mb-1.5 flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Aylık limit</span>
                <span className={`font-mono ${budget.data.exceeded ? "text-rose-500" : budget.data.warning ? "text-amber-500" : "text-foreground"}`}>
                  {money(budget.data.spent, "TRY", 0)} / {money(budget.data.limit, "TRY", 0)} · {percent(budget.data.percent)}
                </span>
              </div>
              <ProgressBar percent={budget.data.percent} exceeded={budget.data.exceeded} testId="gaming-budget-bar" />
              {budget.data.exceeded && <p className="mt-1 text-[10px] font-medium text-rose-500" data-testid="gaming-budget-exceeded">Limit aşıldı — Ayarlar'dan güncelleyebilirsin.</p>}
              {budget.data.warning && <p className="mt-1 text-[10px] font-medium text-amber-500" data-testid="gaming-budget-warning">Limitin %85'ini geçtin.</p>}
            </div>
          )}
          {budget.data?.limit == null && (
            <Link to="/settings" className="mt-4 inline-flex items-center gap-1 rounded-lg border border-dashed border-border px-3 py-2 text-[11px] font-medium text-muted-foreground hover:text-foreground" data-testid="gaming-budget-cta">
              <Wallet2 size={12} /> Aylık Gaming limiti belirle
            </Link>
          )}
          {(summary.data?.top_games ?? []).length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">En çok harcama</p>
              <ul className="space-y-1.5">
                {summary.data!.top_games.map((row) => (
                  <li key={row.game} className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-1.5 text-xs" data-testid={`gaming-top-game-${row.game}`}>
                    <span className="truncate">{row.game}</span>
                    <span className="font-mono font-semibold">{money(row.amount, "TRY", 0)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="mt-4 flex items-center justify-between text-[11px]">
            <Link to="/expenses" className="inline-flex items-center gap-1 font-medium text-primary hover:underline" data-testid="gaming-to-expenses">
              <Wallet2 size={12} /> Giderlerde gör
            </Link>
            {earnings.data && earnings.data.total_commission > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-emerald-500" data-testid="gaming-earnings-chip">
                <Coins size={11} /> {money(earnings.data.total_commission, "TRY", 2)} affiliate kazanç
              </span>
            )}
          </div>
        </Panel>
      </div>

      <Panel testId="gaming-sections">
        <div className="mb-4 flex flex-wrap gap-2">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            const active = s.key === section;
            return (
              <Button
                key={s.key}
                variant={active ? "default" : "outline"}
                size="sm"
                onClick={() => setSection(s.key)}
                className={active ? "bg-primary text-primary-foreground" : ""}
                data-testid={`gaming-section-${s.key}`}
              >
                <Icon size={13} /> {s.label}
              </Button>
            );
          })}
        </div>
        <p className="mb-4 text-xs text-muted-foreground" data-testid="gaming-section-hint">
          {SECTIONS.find((s) => s.key === section)?.hint}
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sectionDeals.map((d) => (
            <DealCard key={d.offer_id} deal={d} testId={`gaming-section-deal-${d.offer_id}`} />
          ))}
          {sectionDeals.length === 0 && <p className="text-xs text-muted-foreground">Şu an bu bölümde ürün yok.</p>}
        </div>
      </Panel>

      <Panel
        title="🔔 Fırsat Uyarıları"
        description="Takibe aldığın ürünler için hedef fiyat düştüğünde burada ve panel uyarılarında görürsün"
        testId="gaming-watches-panel"
      >
        {(watches.data ?? []).length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-xs text-muted-foreground" data-testid="gaming-watches-empty">
            Henüz takip listenizde ürün yok. Ürün sayfasında "Fiyatı takip et" butonuna basarak eklersiniz.
          </p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3" data-testid="gaming-watches-list">
            {watches.data!.map((w) => (
              <li
                key={w.id}
                className={`rounded-xl border p-3 ${w.triggered ? "border-emerald-500/40 bg-emerald-500/10" : "border-border bg-card"}`}
                data-testid={`gaming-watch-${w.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: w.accent_color }}>{w.game_name}</p>
                    <p className="mt-0.5 truncate text-sm font-semibold">{w.product_name}</p>
                  </div>
                  <Bell size={14} className={w.triggered ? "text-emerald-500" : "text-muted-foreground/60"} />
                </div>
                <div className="mt-2 flex items-baseline justify-between text-[11px]">
                  <span className="text-muted-foreground">Hedef</span>
                  <span className="font-mono font-semibold">{money(w.target_price_try, "TRY", 2)}</span>
                </div>
                <div className="mt-1 flex items-baseline justify-between text-[11px]">
                  <span className="text-muted-foreground">Şu an</span>
                  <span className={`font-mono font-semibold ${w.triggered ? "text-emerald-500" : "text-foreground"}`}>{money(w.current_price_try, "TRY", 2)}</span>
                </div>
                {w.triggered && (
                  <p className="mt-2 rounded-lg bg-emerald-500/15 px-2 py-1 text-[10px] font-medium text-emerald-500" data-testid={`gaming-watch-triggered-${w.id}`}>
                    ✅ Hedef fiyata düştü · {w.best_seller_name}
                  </p>
                )}
                <Link to={`/gaming/products/${w.product_id}`} className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline" data-testid={`gaming-watch-goto-${w.id}`}>
                  Ürün sayfasına git <ArrowUpRight size={11} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Tüm oyunlar" description="Kategorine göre keşfet" testId="gaming-all-games">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.all_games.map((g) => (
            <GameTile key={g.slug} game={g} testId={`gaming-game-tile-${g.slug}`} />
          ))}
        </div>
      </Panel>

      <Panel title="Güvenilir satıcılar" description="Güvenilirlik, teslimat ve iade koşulları" testId="gaming-sellers">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.sellers.map((s) => (
            <div key={s.id} className="rounded-xl border border-border bg-card p-4" data-testid={`gaming-seller-${s.id}`}>
              <div className="flex items-center justify-between">
                <p className="font-heading text-sm font-semibold">{s.name}</p>
                <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${reliabilityColor(s.reliability)}`}>
                  <ShieldCheck size={10} /> {reliabilityLabel(s.reliability)}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">{s.domain}</p>
              <p className="mt-2 text-xs text-foreground">
                <span className="text-muted-foreground">Teslimat:</span> {s.delivery}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{s.return_policy}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 rounded-lg border border-border bg-muted/30 p-3 text-[11px] leading-relaxed text-muted-foreground" data-testid="gaming-catalog-note">
          {data.catalog_note}
        </p>
      </Panel>
    </div>
  );
}
