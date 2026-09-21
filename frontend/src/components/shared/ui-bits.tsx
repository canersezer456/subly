import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function PageHeader({ eyebrow, title, description, actions, testId }: { eyebrow: string; title: ReactNode; description?: string; actions?: ReactNode; testId: string }) {
  return (
    <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end" data-testid={testId}>
      <div>
        <p className="mb-1.5 font-mono text-[11px] uppercase tracking-[0.2em] text-primary" data-testid={`${testId}-eyebrow`}>{eyebrow}</p>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground sm:text-3xl" data-testid={`${testId}-title`}>{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground" data-testid={`${testId}-description`}>{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Panel({ title, description, action, children, className, testId }: { title?: string; description?: string; action?: ReactNode; children: ReactNode; className?: string; testId: string }) {
  return (
    <Card className={cn("border-border bg-card p-5 shadow-sm sm:p-6", className)} data-testid={testId}>
      {(title || action) && (
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            {title && <p className="font-heading text-base font-semibold text-foreground" data-testid={`${testId}-title`}>{title}</p>}
            {description && <p className="mt-1 text-xs text-muted-foreground" data-testid={`${testId}-description`}>{description}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </Card>
  );
}

const tones: Record<string, string> = {
  emerald: "bg-emerald-500/12 text-emerald-500",
  rose: "bg-rose-500/12 text-rose-500",
  amber: "bg-amber-500/12 text-amber-500",
  cyan: "bg-cyan-500/12 text-cyan-500",
  indigo: "bg-indigo-500/12 text-indigo-400",
  slate: "bg-muted text-muted-foreground",
};

export function StatCard({ label, value, detail, icon, tone = "slate", to, testId }: { label: string; value: string; detail?: ReactNode; icon: ReactNode; tone?: keyof typeof tones; to?: string; testId: string }) {
  const body = (
    <Card className="group h-full border-border bg-card p-5 transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-primary/40" data-testid={testId}>
      <div className="mb-5 flex items-center justify-between">
        <span className={cn("grid h-9 w-9 place-items-center rounded-lg", tones[tone])}>{icon}</span>
        {to && <ArrowUpRight size={15} className="text-muted-foreground/50 transition-colors group-hover:text-primary" />}
      </div>
      <p className="text-xs text-muted-foreground" data-testid={`${testId}-label`}>{label}</p>
      <p className="mt-1 font-mono text-2xl font-bold tracking-tight text-foreground" data-testid={`${testId}-value`}>{value}</p>
      {detail && <p className="mt-2 truncate text-xs text-muted-foreground" data-testid={`${testId}-detail`}>{detail}</p>}
    </Card>
  );
  return to ? <Link to={to} className="block h-full">{body}</Link> : body;
}

export function EmptyState({ title, description, action, testId }: { title: string; description: string; action?: ReactNode; testId: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border px-6 py-14 text-center" data-testid={testId}>
      <p className="font-heading text-base font-semibold text-foreground">{title}</p>
      <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}

const levelStyles: Record<string, string> = {
  red: "bg-rose-500/12 text-rose-500 border-rose-500/25",
  yellow: "bg-amber-500/12 text-amber-500 border-amber-500/25",
  green: "bg-emerald-500/12 text-emerald-500 border-emerald-500/25",
  warning: "bg-amber-500/12 text-amber-500 border-amber-500/25",
  info: "bg-cyan-500/12 text-cyan-500 border-cyan-500/25",
  success: "bg-emerald-500/12 text-emerald-500 border-emerald-500/25",
};

export function LevelPill({ level, children, testId }: { level: string; children: ReactNode; testId?: string }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium", levelStyles[level] ?? levelStyles.info)} data-testid={testId}>{children}</span>;
}

export function ProgressBar({ percent, exceeded, testId }: { percent: number; exceeded?: boolean; testId?: string }) {
  const width = Math.min(percent, 100);
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted" data-testid={testId}>
      <div className={cn("h-full rounded-full transition-[width] duration-500", exceeded ? "bg-rose-500" : percent >= 85 ? "bg-amber-500" : "bg-primary")} style={{ width: `${width}%` }} />
    </div>
  );
}
