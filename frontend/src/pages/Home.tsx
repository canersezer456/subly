import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { ArrowUpRight, CalendarCheck, PiggyBank, ShieldCheck, Zap } from "lucide-react";
import { apiPost } from "@/lib/api";
import type { AuthPayload, AuthResponse, RegisterPayload } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useMe } from "@/components/layout/AppShell";
import { SBrand } from "@/components/brand/SBrand";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { useT } from "@/lib/i18n";

export default function Home() {
  const me = useMe();
  const { t } = useT();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const onSuccess = (result: AuthResponse) => {
    setError("");
    queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
    queryClient.setQueryData(["me"], result.user);
  };
  const login = useMutation({ mutationFn: (input: AuthPayload) => apiPost<AuthResponse>("/auth/login", input), onSuccess, onError: () => setError(t("auth.error.login")) });
  const register = useMutation({ mutationFn: (input: RegisterPayload) => apiPost<AuthResponse>("/auth/register", input), onSuccess, onError: () => setError(t("auth.error.register")) });
  const busy = login.isPending || register.isPending;

  if (me.data) return <Navigate to="/dashboard" replace />;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (mode === "register") register.mutate({ name, email, password });
    else login.mutate({ email, password });
  };
  const fillDemo = () => { setName("Demo Kullanıcı"); setEmail("demo@subly.app"); setPassword("subly1234"); };
  const googleLogin = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <main className="relative min-h-svh overflow-hidden bg-background text-foreground" data-testid="auth-screen">
      <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
      <div className="absolute -bottom-40 -right-20 h-[30rem] w-[30rem] rounded-full bg-cyan-400/10 blur-3xl" />
      <div className="absolute right-6 top-6 z-10"><LanguageSwitcher /></div>
      <div className="relative mx-auto grid min-h-svh max-w-7xl items-center gap-14 px-6 py-10 lg:grid-cols-[1.15fr_0.85fr] lg:px-10">
        <section className="max-w-2xl" data-testid="auth-hero-content">
          <div className="mb-10 flex items-center gap-3" data-testid="auth-brand">
            <SBrand size={44} rounded="xl" className="shadow-[0_0_30px_rgba(16,185,129,.35)]" />
            <span className="font-heading text-xl font-bold tracking-tight">{t("brand.name")}</span>
          </div>
          <Badge className="mb-6 border border-primary/25 bg-primary/10 px-3 py-1 text-primary" data-testid="auth-eyebrow">{t("auth.eyebrow")}</Badge>
          <h1 className="font-heading text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl" data-testid="auth-headline">{t("auth.headline.a")}<br /><span className="text-primary">{t("auth.headline.b")}</span></h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted-foreground" data-testid="auth-description">{t("auth.description")}</p>
          <div className="mt-12 grid max-w-xl grid-cols-3 gap-4" data-testid="auth-benefits">
            <div><CalendarCheck className="mb-2 text-primary" size={20} /><p className="text-sm font-semibold">{t("auth.benefits.calendar.title")}</p><p className="mt-1 text-xs text-muted-foreground">{t("auth.benefits.calendar.desc")}</p></div>
            <div><PiggyBank className="mb-2 text-amber-500" size={20} /><p className="text-sm font-semibold">{t("auth.benefits.savings.title")}</p><p className="mt-1 text-xs text-muted-foreground">{t("auth.benefits.savings.desc")}</p></div>
            <div><ShieldCheck className="mb-2 text-cyan-500" size={20} /><p className="text-sm font-semibold">{t("auth.benefits.privacy.title")}</p><p className="mt-1 text-xs text-muted-foreground">{t("auth.benefits.privacy.desc")}</p></div>
          </div>
        </section>
        <Card className="relative border-border bg-card/90 p-6 shadow-2xl backdrop-blur-xl sm:p-8" data-testid="auth-card">
          <div className="mb-7">
            <p className="font-heading text-2xl font-bold" data-testid="auth-card-title">{mode === "login" ? t("auth.card.login") : t("auth.card.register")}</p>
            <p className="mt-2 text-sm text-muted-foreground" data-testid="auth-card-description">{t("auth.card.description")}</p>
          </div>
          <div className="mb-6 grid grid-cols-2 rounded-lg bg-muted p-1" data-testid="auth-mode-tabs">
            <button type="button" className={`rounded-md px-3 py-2 text-sm transition-colors ${mode === "login" ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground"}`} onClick={() => setMode("login")} data-testid="auth-login-tab">{t("auth.tab.login")}</button>
            <button type="button" className={`rounded-md px-3 py-2 text-sm transition-colors ${mode === "register" ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground"}`} onClick={() => setMode("register")} data-testid="auth-register-tab">{t("auth.tab.register")}</button>
          </div>
          <form onSubmit={submit} className="space-y-4" data-testid="auth-form">
            {mode === "register" && <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("auth.field.name")} className="h-12" required minLength={2} data-testid="auth-name-input" />}
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("auth.field.email")} className="h-12" required data-testid="auth-email-input" />
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("auth.field.password")} className="h-12" minLength={8} required data-testid="auth-password-input" />
            {error && <p className="text-sm text-rose-500" data-testid="auth-error-message">{error}</p>}
            <Button type="submit" disabled={busy} className="h-12 w-full bg-primary font-semibold text-primary-foreground hover:bg-primary/90" data-testid="login-submit-button">{busy ? t("auth.submit.busy") : mode === "login" ? t("auth.submit.login") : t("auth.submit.register")}<ArrowUpRight className="ml-1" size={17} /></Button>
          </form>
          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" /><span>{t("auth.divider")}</span><span className="h-px flex-1 bg-border" /></div>
          <Button type="button" variant="outline" onClick={googleLogin} className="h-12 w-full" data-testid="google-login-button"><span className="mr-2 grid h-6 w-6 place-items-center rounded-lg bg-white text-xs font-bold text-[#4285F4] shadow-sm">G</span>{t("auth.google")}</Button>
          <Button type="button" variant="ghost" onClick={fillDemo} className="mt-3 h-10 w-full text-xs text-muted-foreground hover:text-primary" data-testid="demo-credentials-fill-button">{t("auth.demo")} <Zap size={13} className="ml-1" /></Button>
          <p className="mt-5 text-center text-[11px] leading-relaxed text-muted-foreground" data-testid="auth-security-note"><ShieldCheck size={13} className="mr-1 inline text-primary" />{t("auth.security")}</p>
        </Card>
      </div>
    </main>
  );
}
