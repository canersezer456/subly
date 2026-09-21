import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, PiggyBank, Sparkles } from "lucide-react";
import { apiGet } from "@/lib/api";
import { money } from "@/lib/format";
import type { SavingsReport } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EmptyState, LevelPill, PageHeader, Panel } from "@/components/shared/ui-bits";

const LEVEL_LABEL = { red: "🔴 Hemen bak", yellow: "🟡 Değerlendir", green: "🟢 Fırsat" };

export default function Savings() {
  const { data, isLoading } = useQuery({ queryKey: ["savings"], queryFn: () => apiGet<SavingsReport>("/savings"), retry: false });
  const insights = data?.insights ?? [];

  return (
    <div data-testid="savings-page">
      <PageHeader eyebrow="Tasarruf motoru" title="Nereden tasarruf edebilirsin?" description="Verilerine bakarak kullanılmayan abonelikleri, aşılan bütçeleri, yükselen faturaları ve daha uygun plan alternatiflerini buluyoruz. Karar senin; biz yalnızca gösteriyoruz." testId="savings-header" />

      <section className="mb-6 rounded-2xl border border-primary/25 bg-gradient-to-br from-primary/15 via-card to-card p-6 sm:p-8" data-testid="savings-hero">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="flex items-center gap-2 text-sm text-muted-foreground"><PiggyBank size={16} className="text-primary" /> 💰 Bu ay potansiyel tasarruf</p>
            <p className="mt-2 font-mono text-4xl font-bold tracking-tight sm:text-5xl" data-testid="savings-total">{money(data?.total ?? 0)}</p>
            <p className="mt-2 text-sm text-muted-foreground" data-testid="savings-summary-line">{insights.length} fırsat · {data?.unused_subscriptions ?? 0} kullanılmayan abonelik</p>
          </div>
          <Button render={<Link to="/assistant" />} variant="outline" data-testid="savings-ask-assistant"><Sparkles size={15} /> Asistana “nasıl azaltırım?” diye sor</Button>
        </div>
      </section>

      <Panel title="Neden?" description="Tutar, aylık kazanım tahminidir" testId="savings-list">
        {isLoading ? <p className="text-sm text-muted-foreground">Analiz ediliyor…</p> : insights.length === 0 ? <EmptyState title="Şu an belirgin bir tasarruf fırsatı yok" description="Aboneliklerinin kullanım durumunu işaretle ve bütçe tanımla; motor yeni fırsatlar bulduğunda burada listeler." testId="savings-empty" /> : (
          <ul className="space-y-3">
            {insights.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-background/50 p-4 transition-[border-color] hover:border-primary/40" data-testid={`insight-${i.id}`}>
                <LevelPill level={i.level} testId={`insight-level-${i.id}`}>{LEVEL_LABEL[i.level]}</LevelPill>
                <div className="min-w-[12rem] flex-1">
                  <p className="text-sm font-semibold" data-testid={`insight-title-${i.id}`}>{i.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground" data-testid={`insight-detail-${i.id}`}>{i.detail}</p>
                </div>
                <p className="font-mono text-lg font-bold text-primary" data-testid={`insight-amount-${i.id}`}>{money(i.amount)}</p>
                <Button render={<Link to={i.action_path} />} variant="ghost" size="sm" className="text-primary" data-testid={`insight-action-${i.id}`}>{i.action_label} <ArrowRight size={13} /></Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
