import { useEffect, useState } from "react";
import { Download, Smartphone, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const { t } = useT();
  const [promptEvent, setPromptEvent] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const handlePrompt = (event: Event) => {
      event.preventDefault();
      setPromptEvent(event as InstallPromptEvent);
    };
    const handleInstalled = () => {
      setInstalled(true);
      setPromptEvent(null);
    };
    window.addEventListener("beforeinstallprompt", handlePrompt);
    window.addEventListener("appinstalled", handleInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handlePrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  const install = async () => {
    if (!promptEvent) return;
    await promptEvent.prompt();
    const choice = await promptEvent.userChoice;
    if (choice.outcome === "accepted") setInstalled(true);
    setPromptEvent(null);
  };

  return (
    <section className="relative overflow-hidden rounded-[1.75rem] border border-cyan-300/20 bg-gradient-to-br from-cyan-400/15 via-indigo-400/10 to-fuchsia-400/10 p-6 sm:p-8" data-testid="install-app-panel">
      <div className="absolute -right-10 -top-16 h-48 w-48 rounded-full bg-cyan-300/15 blur-3xl" />
      <div className="relative grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
        <div>
          <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200" data-testid="install-app-eyebrow"><Smartphone size={15} /> {t("install.eyebrow")}</div>
          <h2 className="font-heading text-2xl font-bold text-white sm:text-3xl" data-testid="install-app-title">{t("install.title")}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-300" data-testid="install-app-description">{t("install.description")}</p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs" data-testid="install-readiness-badges"><span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-slate-200">{t("install.badge.ios")}</span><span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-slate-200">{t("install.badge.android")}</span><span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-slate-200">{t("install.badge.store")}</span></div>
        </div>
        <Button onClick={install} disabled={!promptEvent || installed} className="h-12 rounded-2xl bg-white px-6 font-semibold text-slate-950 hover:bg-cyan-50 disabled:opacity-70" data-testid="install-subly-button">
          {installed ? <><Sparkles size={17} className="mr-2" />{t("install.installed")}</> : <><Download size={17} className="mr-2" />{promptEvent ? t("install.installNow") : t("install.ready")}</>}
        </Button>
      </div>
    </section>
  );
}
