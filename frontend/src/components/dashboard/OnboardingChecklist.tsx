import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Circle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { dismissOnboarding } from "@/lib/onboarding";
import { useT } from "@/lib/i18n";
import type { DashboardSummary } from "@/lib/types";

interface Step {
  key: string;
  label: string;
  desc: string;
  done: boolean;
  to: string;
  action: string;
}

// Frontend-only welcome checklist for new accounts — no backend flag backs this.
// Points at existing pages (income/expense/budget/subscriptions) instead of
// duplicating their forms here. Never blocks navigation; always dismissible.
export function OnboardingChecklist({ userId, userName, data, onDismiss }: { userId: string; userName: string; data: DashboardSummary; onDismiss: () => void }) {
  const { t } = useT();
  const steps: Step[] = [
    { key: "income", label: t("onboarding.step.income.label"), desc: t("onboarding.step.income.desc"), done: data.income_total > 0, to: "/incomes", action: t("onboarding.step.income.action") },
    { key: "expense", label: t("onboarding.step.expense.label"), desc: t("onboarding.step.expense.desc"), done: data.expense_total > 0, to: "/expenses", action: t("onboarding.step.expense.action") },
    { key: "budget", label: t("onboarding.step.budget.label"), desc: t("onboarding.step.budget.desc"), done: data.budgets.length > 0, to: "/budget", action: t("onboarding.step.budget.action") },
    { key: "subs", label: t("onboarding.step.subs.label"), desc: t("onboarding.step.subs.desc"), done: data.subscription_monthly > 0 || data.subscription_yearly > 0, to: "/subscriptions", action: t("onboarding.step.subs.action") },
  ];
  const completed = steps.filter((s) => s.done).length;

  useEffect(() => {
    if (completed === steps.length) {
      dismissOnboarding(userId);
      onDismiss();
    }
    // Only re-check when completion count changes — dismiss() + onDismiss() are stable no-ops otherwise.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completed]);

  const dismiss = () => {
    dismissOnboarding(userId);
    onDismiss();
  };

  return (
    <Card className="mb-6 border-primary/25 bg-primary/[0.04] p-5 sm:p-6" data-testid="onboarding-checklist">
      <div className="mb-1 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <p className="font-heading text-lg font-semibold text-foreground" data-testid="onboarding-title">{t("onboarding.title", { name: userName.split(" ")[0] })}</p>
          <p className="mt-1 text-sm text-muted-foreground" data-testid="onboarding-description">{t("onboarding.description")}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2 self-end sm:self-auto">
          <span className="rounded-full bg-muted px-2.5 py-1 font-mono text-xs text-muted-foreground" data-testid="onboarding-progress">{completed}/{steps.length}</span>
          <Button variant="ghost" size="icon-sm" onClick={dismiss} aria-label={t("onboarding.dismiss")} data-testid="onboarding-dismiss"><X size={14} /></Button>
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step) => (
          <div key={step.key} className={`rounded-xl border p-3.5 ${step.done ? "border-border bg-card/40" : "border-border bg-card"}`} data-testid={`onboarding-step-${step.key}`}>
            <div className="flex items-center gap-2">
              {step.done ? <CheckCircle2 size={16} className="text-primary" /> : <Circle size={16} className="text-muted-foreground" />}
              <p className={`text-sm font-medium ${step.done ? "text-muted-foreground line-through decoration-muted-foreground/50" : "text-foreground"}`}>{step.label}</p>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{step.desc}</p>
            {!step.done && (
              <Button render={<Link to={step.to} />} variant="outline" size="sm" className="mt-3 h-8 text-xs" data-testid={`onboarding-step-${step.key}-action`}>{step.action}</Button>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
