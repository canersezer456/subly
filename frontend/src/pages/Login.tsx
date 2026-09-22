import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowUpRight, CalendarCheck, Loader2, PiggyBank, ShieldCheck, Zap } from "lucide-react";
import { ApiError, apiPost } from "@/lib/api";
import type { AuthPayload, AuthResponse, RegisterPayload } from "@/lib/types";
import { markOnboardingStarted } from "@/lib/onboarding";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useMe } from "@/components/layout/AppShell";
import { SBrand } from "@/components/brand/SBrand";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { useT } from "@/lib/i18n";

type Mode = "login" | "register";
type FieldErrors = Partial<Record<"name" | "email" | "password", string>>;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const me = useMe();
  const { t } = useT();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<Mode>(searchParams.get("mode") === "register" ? "register" : "login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState("");

  const onSuccess = (result: AuthResponse) => {
    setFormError("");
    setFieldErrors({});
    queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
    queryClient.setQueryData(["me"], result.user);
  };

  const login = useMutation({
    mutationFn: (input: AuthPayload) => apiPost<AuthResponse>("/auth/login", input),
    onSuccess,
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) setFormError(t("auth.error.login"));
      else setFormError(t("auth.error.network"));
    },
  });
  const register = useMutation({
    mutationFn: (input: RegisterPayload) => apiPost<AuthResponse>("/auth/register", input),
    onSuccess: (result) => {
      markOnboardingStarted(result.user.user_id);
      onSuccess(result);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 409) setFormError(t("auth.error.emailTaken"));
      else if (err instanceof ApiError && err.status === 422) setFormError(t("auth.error.invalid"));
      else setFormError(t("auth.error.network"));
    },
  });
  const busy = login.isPending || register.isPending;

  if (me.data) return <Navigate to="/dashboard" replace />;

  const validate = (): boolean => {
    const errors: FieldErrors = {};
    if (mode === "register" && name.trim().length < 2) errors.name = t("auth.validation.name");
    if (!EMAIL_RE.test(email.trim())) errors.email = t("auth.validation.email");
    if (password.length < 8) errors.password = t("auth.validation.password");
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setFormError("");
    if (!validate()) return;
    if (mode === "register") register.mutate({ name: name.trim(), email: email.trim(), password });
    else login.mutate({ email: email.trim(), password });
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    setFieldErrors({});
    setFormError("");
  };

  const fillDemo = () => {
    setName("Demo Kullanıcı");
    setEmail("demo@subly.app");
    setPassword("subly1234");
    setFieldErrors({});
    setFormError("");
  };
  const googleLogin = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <main className="relative min-h-svh overflow-hidden bg-background text-foreground" data-testid="auth-screen">
      <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
      <div className="absolute -bottom-40 -right-20 h-[30rem] w-[30rem] rounded-full bg-cyan-400/10 blur-3xl" />
      <div className="relative mx-auto flex max-w-7xl items-center justify-between gap-3 px-6 pt-6 lg:px-10">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground" data-testid="auth-back-to-landing">
          <ArrowLeft size={15} /> {t("auth.backToLanding")}
        </Link>
        <LanguageSwitcher />
      </div>
      <div className="relative mx-auto grid min-h-[calc(100svh-4rem)] max-w-7xl items-center gap-14 px-6 py-10 lg:grid-cols-[1.15fr_0.85fr] lg:px-10">
        <section className="order-2 max-w-2xl lg:order-1" data-testid="auth-hero-content">
          <div className="mb-10 hidden items-center gap-3 lg:flex" data-testid="auth-brand">
            <SBrand size={44} rounded="xl" className="shadow-[0_0_30px_rgba(16,185,129,.35)]" />
            <span className="font-heading text-xl font-bold tracking-tight">{t("brand.name")}</span>
          </div>
          <Badge className="mb-6 border border-primary/25 bg-primary/10 px-3 py-1 text-primary" data-testid="auth-eyebrow">{t("auth.eyebrow")}</Badge>
          <h1 className="font-heading text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl" data-testid="auth-headline">{t("auth.headline.a")}<br /><span className="text-primary">{t("auth.headline.b")}</span></h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg" data-testid="auth-description">{t("auth.description")}</p>
          <div className="mt-10 grid max-w-xl grid-cols-3 gap-4" data-testid="auth-benefits">
            <div><CalendarCheck className="mb-2 text-primary" size={20} /><p className="text-sm font-semibold">{t("auth.benefits.calendar.title")}</p><p className="mt-1 text-xs text-muted-foreground">{t("auth.benefits.calendar.desc")}</p></div>
            <div><PiggyBank className="mb-2 text-amber-500" size={20} /><p className="text-sm font-semibold">{t("auth.benefits.savings.title")}</p><p className="mt-1 text-xs text-muted-foreground">{t("auth.benefits.savings.desc")}</p></div>
            <div><ShieldCheck className="mb-2 text-cyan-500" size={20} /><p className="text-sm font-semibold">{t("auth.benefits.privacy.title")}</p><p className="mt-1 text-xs text-muted-foreground">{t("auth.benefits.privacy.desc")}</p></div>
          </div>
        </section>
        <Card className="relative order-1 border-border bg-card/90 p-6 shadow-2xl backdrop-blur-xl sm:p-8 lg:order-2" data-testid="auth-card">
          <div className="mb-3 flex items-center gap-2.5 lg:hidden">
            <SBrand size={32} rounded="lg" />
            <span className="font-heading text-base font-bold tracking-tight">{t("brand.name")}</span>
          </div>
          <div className="mb-7">
            <p className="font-heading text-2xl font-bold" data-testid="auth-card-title">{mode === "login" ? t("auth.card.login") : t("auth.card.register")}</p>
            <p className="mt-2 text-sm text-muted-foreground" data-testid="auth-card-description">{t("auth.card.description")}</p>
          </div>
          <div className="mb-6 grid grid-cols-2 rounded-lg bg-muted p-1" data-testid="auth-mode-tabs">
            <button type="button" className={`rounded-md px-3 py-2 text-sm transition-colors ${mode === "login" ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground"}`} onClick={() => switchMode("login")} data-testid="auth-login-tab">{t("auth.tab.login")}</button>
            <button type="button" className={`rounded-md px-3 py-2 text-sm transition-colors ${mode === "register" ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground"}`} onClick={() => switchMode("register")} data-testid="auth-register-tab">{t("auth.tab.register")}</button>
          </div>
          <form onSubmit={submit} noValidate className="space-y-4" data-testid="auth-form">
            {mode === "register" && (
              <div>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("auth.field.name")} className="h-12" disabled={busy} aria-invalid={Boolean(fieldErrors.name)} data-testid="auth-name-input" />
                {fieldErrors.name && <p className="mt-1.5 text-xs text-rose-500" data-testid="auth-name-error">{fieldErrors.name}</p>}
              </div>
            )}
            <div>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("auth.field.email")} className="h-12" disabled={busy} aria-invalid={Boolean(fieldErrors.email)} data-testid="auth-email-input" />
              {fieldErrors.email && <p className="mt-1.5 text-xs text-rose-500" data-testid="auth-email-error">{fieldErrors.email}</p>}
            </div>
            <div>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("auth.field.password")} className="h-12" disabled={busy} aria-invalid={Boolean(fieldErrors.password)} data-testid="auth-password-input" />
              {fieldErrors.password && <p className="mt-1.5 text-xs text-rose-500" data-testid="auth-password-error">{fieldErrors.password}</p>}
            </div>
            {formError && <p className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-500" data-testid="auth-error-message">{formError}</p>}
            <Button type="submit" disabled={busy} className="h-12 w-full bg-primary font-semibold text-primary-foreground hover:bg-primary/90" data-testid="login-submit-button">
              {busy ? <><Loader2 className="animate-spin" size={16} /> {t("auth.submit.busy")}</> : <>{mode === "login" ? t("auth.submit.login") : t("auth.submit.register")}<ArrowUpRight className="ml-1" size={17} /></>}
            </Button>
          </form>
          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" /><span>{t("auth.divider")}</span><span className="h-px flex-1 bg-border" /></div>
          <Button type="button" variant="outline" onClick={googleLogin} disabled={busy} className="h-12 w-full" data-testid="google-login-button"><span className="mr-2 grid h-6 w-6 place-items-center rounded-lg bg-white text-xs font-bold text-[#4285F4] shadow-sm">G</span>{t("auth.google")}</Button>
          <Button type="button" variant="ghost" onClick={fillDemo} disabled={busy} className="mt-3 h-10 w-full text-xs text-muted-foreground hover:text-primary" data-testid="demo-credentials-fill-button">{t("auth.demo")} <Zap size={13} className="ml-1" /></Button>
          <p className="mt-5 text-center text-[11px] leading-relaxed text-muted-foreground" data-testid="auth-security-note"><ShieldCheck size={13} className="mr-1 inline text-primary" />{t("auth.security")}</p>
        </Card>
      </div>
    </main>
  );
}
