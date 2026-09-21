import { Link } from "react-router-dom";
import { Home, Lock, Split, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LevelPill, PageHeader, Panel } from "@/components/shared/ui-bits";

const ROADMAP = [
  { icon: Users, title: "Ev üyeleri", text: "Eşin, çocuğun veya ev arkadaşını davet et; herkes kendi cihazından aynı ev ekonomisini görsün." },
  { icon: Split, title: "Ortak gider bölüşme", text: "Kira, elektrik, market gibi ortak giderleri kişi başı payla. “Caner elektrik faturasının kendi payı olan ₺450'yi ödedi.” gibi kayıtlar." },
  { icon: Lock, title: "Kim ne kadar ödedi?", text: "Aylık bakiye: kimin alacağı, kimin borcu var tek bakışta." },
];

export default function Household() {
  return (
    <div data-testid="household-page">
      <PageHeader eyebrow="Ev ekonomisi" title="Ev" description="Bireysel finansını oturttuktan sonra aynı düzeni ev halkıyla paylaşabileceksin. Bu modül ilk sürümde planlama aşamasında." testId="household-header" />
      <section className="mb-6 rounded-2xl border border-border bg-card p-6 sm:p-8" data-testid="household-hero">
        <div className="flex flex-wrap items-center gap-4">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-500/15 text-indigo-400"><Home size={22} /></span>
          <div className="flex-1">
            <div className="flex items-center gap-2"><p className="font-heading text-lg font-semibold">Ortak ev henüz oluşturulmadı</p><LevelPill level="info" testId="household-status">Yakında</LevelPill></div>
            <p className="mt-1 text-sm text-muted-foreground">Veri modeli çok kullanıcılı yapıya hazır; ev davetleri ve bölüşme akışı sonraki sürümde açılacak.</p>
          </div>
          <Button render={<Link to="/bills" />} variant="outline" data-testid="household-go-bills">Şimdilik ortak faturaları ekle</Button>
        </div>
      </section>
      <div className="grid gap-4 md:grid-cols-3" data-testid="household-roadmap">
        {ROADMAP.map((item) => { const Icon = item.icon; return (
          <Panel key={item.title} testId={`household-roadmap-${item.title}`}>
            <Icon size={18} className="mb-3 text-primary" />
            <p className="text-sm font-semibold">{item.title}</p>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{item.text}</p>
          </Panel>
        ); })}
      </div>
    </div>
  );
}
