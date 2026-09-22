import { Link } from "react-router-dom";
import { Home, Lock, Split, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { LevelPill, PageHeader, Panel } from "@/components/shared/ui-bits";

export default function Household() {
  const { t } = useT();
  const ROADMAP = [
    { key: "members", icon: Users },
    { key: "split", icon: Split },
    { key: "balance", icon: Lock },
  ];

  return (
    <div data-testid="household-page">
      <PageHeader eyebrow={t("household.eyebrow")} title={t("household.title")} description={t("household.description")} testId="household-header" />
      <section className="mb-6 rounded-2xl border border-border bg-card p-6 sm:p-8" data-testid="household-hero">
        <div className="flex flex-wrap items-center gap-4">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-500/15 text-indigo-400"><Home size={22} /></span>
          <div className="flex-1">
            <div className="flex items-center gap-2"><p className="font-heading text-lg font-semibold">{t("household.status.title")}</p><LevelPill level="info" testId="household-status">{t("household.status.badge")}</LevelPill></div>
            <p className="mt-1 text-sm text-muted-foreground">{t("household.status.desc")}</p>
          </div>
          <Button render={<Link to="/bills" />} variant="outline" data-testid="household-go-bills">{t("household.cta")}</Button>
        </div>
      </section>
      <div className="grid gap-4 md:grid-cols-3" data-testid="household-roadmap">
        {ROADMAP.map((item) => { const Icon = item.icon; return (
          <Panel key={item.key} testId={`household-roadmap-${item.key}`}>
            <Icon size={18} className="mb-3 text-primary" />
            <p className="text-sm font-semibold">{t(`household.roadmap.${item.key}.title`)}</p>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{t(`household.roadmap.${item.key}.text`)}</p>
          </Panel>
        ); })}
      </div>
    </div>
  );
}
