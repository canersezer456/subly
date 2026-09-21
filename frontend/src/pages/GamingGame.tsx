import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Sparkles, Timer } from "lucide-react";
import { apiGet } from "@/lib/api";
import { money } from "@/lib/format";
import type { GamingGameDetail } from "@/lib/types";
import { PageHeader, Panel } from "@/components/shared/ui-bits";

const TAG_LABEL: Record<string, string> = { popular: "Popüler", best_value: "En Avantajlı", new: "Yeni" };
const TAG_COLOR: Record<string, string> = {
  popular: "bg-fuchsia-500/12 text-fuchsia-400 border-fuchsia-500/25",
  best_value: "bg-emerald-500/12 text-emerald-500 border-emerald-500/25",
  new: "bg-cyan-500/12 text-cyan-500 border-cyan-500/25",
};

export default function GamingGame() {
  const { slug = "" } = useParams();
  const game = useQuery({
    queryKey: ["gaming", "game", slug],
    queryFn: () => apiGet<GamingGameDetail>(`/gaming/games/${slug}`),
    enabled: Boolean(slug),
    staleTime: 60_000,
  });

  if (game.isLoading) return <div className="grid min-h-[50svh] place-items-center text-sm text-muted-foreground" data-testid="gaming-game-loading">Oyun yükleniyor…</div>;
  if (game.error || !game.data) return <div className="grid min-h-[50svh] place-items-center text-sm text-rose-500" data-testid="gaming-game-error">Oyun bulunamadı.</div>;
  const g = game.data;

  return (
    <div className="space-y-6" data-testid="gaming-game-page">
      <Link to="/gaming" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-testid="gaming-game-back">
        <ArrowLeft size={13} /> Gaming ana sayfası
      </Link>

      <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 sm:flex-row sm:items-center" data-testid="gaming-game-hero" style={{ borderColor: `${g.accent_color}55` }}>
        <span
          className="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-2xl"
          style={{ backgroundColor: `${g.accent_color}22`, color: g.accent_color }}
        >
          <img src={g.icon_url} alt="" className="h-12 w-12 object-contain" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] uppercase tracking-wider" style={{ color: g.accent_color }}>{g.category} · {g.currency}</p>
          <h1 className="font-heading text-2xl font-bold text-foreground" data-testid="gaming-game-title">{g.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{g.tagline}</p>
        </div>
        {g.best_price_try != null && (
          <div className="text-right">
            <p className="text-[11px] text-muted-foreground">Başlangıç</p>
            <p className="font-mono text-lg font-bold text-foreground" data-testid="gaming-game-start-price">{money(g.best_price_try, "TRY", 0)}</p>
          </div>
        )}
      </div>

      <PageHeader eyebrow="Ürünler" title="Hangi paketi almak istiyorsun?" description="En uygun teklif ve teslimat süresi ürün sayfasında karşılaştırılır." testId="gaming-products-header" />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="gaming-game-products">
        {g.products.map((p) => (
          <Link
            key={p.id}
            to={`/gaming/products/${p.id}`}
            className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-[border-color,transform] hover:-translate-y-0.5 hover:border-primary/40"
            data-testid={`gaming-product-${p.id}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{p.game_currency}</p>
                <p className="mt-0.5 font-heading text-base font-semibold">{p.name}</p>
              </div>
              {p.tag && (
                <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${TAG_COLOR[p.tag]}`}>
                  <Sparkles size={10} /> {TAG_LABEL[p.tag]}
                </span>
              )}
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground">En düşük fiyat</p>
              <p className="font-mono text-xl font-bold text-foreground" data-testid={`gaming-product-price-${p.id}`}>
                {p.best_price_try != null ? money(p.best_price_try, "TRY", 2) : "-"}
              </p>
            </div>
            <p className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              <Timer size={11} /> {p.offer_count} satıcıdan karşılaştır
            </p>
          </Link>
        ))}
        {g.products.length === 0 && (
          <Panel testId="gaming-game-empty">
            <p className="text-sm text-muted-foreground">Bu oyunda henüz ürün yok.</p>
          </Panel>
        )}
      </div>
    </div>
  );
}
