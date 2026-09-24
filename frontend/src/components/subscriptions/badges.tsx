import { Database, History, Import, Mail, PenLine } from "lucide-react";
import type { SubscriptionSource } from "@/lib/types";
import type { Translate } from "@/lib/subscriptionUi";
import { cn } from "@/lib/utils";

const SOURCE_STYLE: Record<SubscriptionSource, { icon: typeof Mail; className: string }> = {
  manual: { icon: PenLine, className: "border-slate-400/25 bg-slate-400/10 text-muted-foreground" },
  email: { icon: Mail, className: "border-cyan-500/25 bg-cyan-500/10 text-cyan-500" },
  transaction: { icon: Database, className: "border-emerald-500/25 bg-emerald-500/10 text-emerald-500" },
  import: { icon: Import, className: "border-indigo-400/25 bg-indigo-400/10 text-indigo-400" },
  legacy: { icon: History, className: "border-amber-500/25 bg-amber-500/10 text-amber-500" },
};

/** Where a subscription row came from. "legacy" = predates source tracking (never claimed as verified). */
export function SourceBadge({ source, t }: { source: SubscriptionSource; t: Translate }) {
  const style = SOURCE_STYLE[source] ?? SOURCE_STYLE.manual;
  const Icon = style.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium", style.className)} data-testid="subscription-source-badge" data-source={source}>
      <Icon size={10} aria-hidden="true" /> {t(`subsHub.source.${source}`)}
    </span>
  );
}

const CONFIDENCE_STYLE: Record<string, string> = {
  high: "border-emerald-500/25 bg-emerald-500/10 text-emerald-500",
  medium: "border-cyan-500/25 bg-cyan-500/10 text-cyan-500",
  review: "border-amber-500/25 bg-amber-500/10 text-amber-500",
};

/** Descriptive confidence bucket — the numeric score is never shown as false precision. */
export function ConfidenceBadge({ label, t }: { label: string; t: Translate }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium", CONFIDENCE_STYLE[label] ?? CONFIDENCE_STYLE.review)} data-testid="candidate-confidence" data-confidence={label}>
      {t(`subsHub.confidence.${label}`)}
    </span>
  );
}
