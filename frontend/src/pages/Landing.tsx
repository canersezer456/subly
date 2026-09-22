import type { ReactNode } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowUpRight, Bell, Bot, CalendarDays, CreditCard, PieChart, PiggyBank, Receipt, ShieldCheck, Target, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SBrand } from "@/components/brand/SBrand";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { useMe } from "@/components/layout/AppShell";
import { useT } from "@/lib/i18n";

function FeatureCard({ icon, title, desc, tone, testId }: { icon: ReactNode; title: string; desc: string; tone: string; testId: string }) {
  return (
    <Card className="border-border bg-card p-6 transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-primary/40" data-testid={testId}>
      <span className={`grid h-11 w-11 place-items-center rounded-xl ${tone}`}>{icon}</span>
      <p className="mt-4 font-heading text-base font-semibold text-foreground">{title}</p>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{desc}</p>
    </Card>
  );
}

function PreviewCard({ icon, title, desc, testId }: { icon: ReactNode; title: string; desc: string; testId: string }) {
  return (
    <div className="rounded-xl border border-border bg-card/60 p-5" data-testid={testId}>
      <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary/12 text-primary">{icon}</span>
      <p className="mt-3 text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{desc}</p>
    </div>
  );
}

export default function Landing() {
  const me = useMe();
  const { t } = useT();

  if (me.data) return <Navigate to="/dashboard" replace />;

  const features = [
    { icon: <Wallet size={19} />, tone: "bg-emerald-500/12 text-emerald-500", title: t("landing.feature.money.title"), desc: t("landing.feature.money.desc"), testId: "landing-feature-money" },
    { icon: <CreditCard size={19} />, tone: "bg-indigo-500/12 text-indigo-400", title: t("landing.feature.subs.title"), desc: t("landing.feature.subs.desc"), testId: "landing-feature-subs" },
    { icon: <CalendarDays size={19} />, tone: "bg-cyan-500/12 text-cyan-500", title: t("landing.feature.bills.title"), desc: t("landing.feature.bills.desc"), testId: "landing-feature-bills" },
    { icon: <Target size={19} />, tone: "bg-amber-500/12 text-amber-500", title: t("landing.feature.budget.title"), desc: t("landing.feature.budget.desc"), testId: "landing-feature-budget" },
    { icon: <PiggyBank size={19} />, tone: "bg-rose-500/12 text-rose-500", title: t("landing.feature.savings.title"), desc: t("landing.feature.savings.desc"), testId: "landing-feature-savings" },
    { icon: <Bot size={19} />, tone: "bg-primary/12 text-primary", title: t("landing.feature.assistant.title"), desc: t("landing.feature.assistant.desc"), testId: "landing-feature-assistant" },
  ];

  return (
    <main className="min-h-svh bg-background text-foreground" data-testid="landing-page">
      <header className="sticky top-0 z-30 border-b border-border bg-background/85 px-4 py-3.5 backdrop-blur-xl sm:px-6 lg:px-10" data-testid="landing-header">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5" data-testid="landing-brand">
            <SBrand size={32} rounded="lg" />
            <span className="hidden font-heading text-base font-bold tracking-tight sm:inline">{t("brand.name")}</span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <LanguageSwitcher compact />
            <Button render={<Link to="/login" />} variant="ghost" size="sm" className="sm:h-8 sm:px-2.5 sm:text-sm" data-testid="landing-nav-login">{t("landing.nav.login")}</Button>
            <Button render={<Link to="/login?mode=register" />} size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90 sm:h-8 sm:px-2.5 sm:text-sm" data-testid="landing-nav-register">
              <span className="sm:hidden">{t("landing.nav.registerShort")}</span>
              <span className="hidden sm:inline">{t("landing.nav.register")}</span>
            </Button>
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:px-10" data-testid="landing-hero">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute -right-20 top-10 h-[26rem] w-[26rem] rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="relative mx-auto max-w-3xl text-center">
          <Badge className="mb-6 border border-primary/25 bg-primary/10 px-3 py-1 text-primary" data-testid="landing-hero-eyebrow">{t("landing.hero.eyebrow")}</Badge>
          <h1 className="font-heading text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl" data-testid="landing-hero-headline">
            {t("landing.hero.headline.a")} <span className="text-primary">{t("landing.hero.headline.b")}</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg" data-testid="landing-hero-description">{t("landing.hero.description")}</p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row" data-testid="landing-hero-actions">
            <Button render={<Link to="/login?mode=register" />} className="h-12 w-full bg-primary px-6 font-semibold text-primary-foreground hover:bg-primary/90 sm:w-auto" data-testid="landing-hero-cta-primary">
              {t("landing.hero.cta.primary")} <ArrowUpRight size={17} />
            </Button>
            <Button render={<Link to="/login" />} variant="outline" className="h-12 w-full px-6 sm:w-auto" data-testid="landing-hero-cta-secondary">{t("landing.hero.cta.secondary")}</Button>
          </div>
          <p className="mt-5 text-xs text-muted-foreground" data-testid="landing-hero-note">{t("landing.hero.note")}</p>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 sm:py-20 lg:px-10" data-testid="landing-features">
        <div className="mx-auto max-w-6xl">
          <div className="mx-auto max-w-2xl text-center">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-primary" data-testid="landing-features-eyebrow">{t("landing.features.eyebrow")}</p>
            <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="landing-features-title">{t("landing.features.title")}</h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base" data-testid="landing-features-description">{t("landing.features.description")}</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => <FeatureCard key={f.testId} {...f} />)}
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 sm:py-20 lg:px-10" data-testid="landing-preview">
        <div className="mx-auto max-w-6xl rounded-3xl border border-border bg-card/40 p-6 sm:p-10">
          <div className="mx-auto max-w-2xl text-center">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-primary" data-testid="landing-preview-eyebrow">{t("landing.preview.eyebrow")}</p>
            <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="landing-preview-title">{t("landing.preview.title")}</h2>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <PreviewCard icon={<Wallet size={17} />} title={t("landing.preview.summary.title")} desc={t("landing.preview.summary.desc")} testId="landing-preview-summary" />
            <PreviewCard icon={<Receipt size={17} />} title={t("landing.preview.upcoming.title")} desc={t("landing.preview.upcoming.desc")} testId="landing-preview-upcoming" />
            <PreviewCard icon={<PieChart size={17} />} title={t("landing.preview.categories.title")} desc={t("landing.preview.categories.desc")} testId="landing-preview-categories" />
            <PreviewCard icon={<Bell size={17} />} title={t("landing.preview.alerts.title")} desc={t("landing.preview.alerts.desc")} testId="landing-preview-alerts" />
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 sm:py-20 lg:px-10" data-testid="landing-trust">
        <div className="mx-auto max-w-3xl rounded-2xl border border-border bg-card p-6 sm:p-8">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/12 text-primary"><ShieldCheck size={20} /></span>
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-primary" data-testid="landing-trust-eyebrow">{t("landing.trust.eyebrow")}</p>
              <p className="font-heading text-lg font-semibold" data-testid="landing-trust-title">{t("landing.trust.title")}</p>
            </div>
          </div>
          <ul className="space-y-2.5 text-sm leading-relaxed text-muted-foreground" data-testid="landing-trust-points">
            <li>• {t("landing.trust.point.hash")}</li>
            <li>• {t("landing.trust.point.export")}</li>
            <li>• {t("landing.trust.point.mock")}</li>
          </ul>
        </div>
      </section>

      <section className="px-4 pb-20 sm:px-6 lg:px-10" data-testid="landing-cta">
        <div className="relative mx-auto max-w-4xl overflow-hidden rounded-[1.75rem] border border-primary/25 bg-gradient-to-br from-primary/15 via-cyan-400/10 to-fuchsia-400/10 p-8 text-center sm:p-12">
          <div className="absolute -right-10 -top-16 h-48 w-48 rounded-full bg-primary/20 blur-3xl" />
          <h2 className="relative font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="landing-cta-title">{t("landing.cta.title")}</h2>
          <p className="relative mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base" data-testid="landing-cta-description">{t("landing.cta.description")}</p>
          <Button render={<Link to="/login?mode=register" />} className="relative mt-7 h-12 bg-primary px-7 font-semibold text-primary-foreground hover:bg-primary/90" data-testid="landing-cta-button">
            {t("landing.cta.button")} <ArrowUpRight size={17} />
          </Button>
        </div>
      </section>

      <footer className="border-t border-border px-4 py-8 sm:px-6 lg:px-10" data-testid="landing-footer">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <SBrand size={26} rounded="md" />
            <span className="text-sm font-semibold">{t("brand.name")}</span>
            <span className="text-xs text-muted-foreground">— {t("brand.tagline")}</span>
          </div>
          <p className="text-xs text-muted-foreground" data-testid="landing-footer-copyright">© {new Date().getFullYear()} Subly. {t("landing.footer.rights")}</p>
        </div>
      </footer>
    </main>
  );
}
