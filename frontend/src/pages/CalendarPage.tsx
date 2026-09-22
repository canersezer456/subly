import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { apiGet } from "@/lib/api";
import { money, monthIso } from "@/lib/format";
import { useMoney } from "@/lib/currency";
import { useT } from "@/lib/i18n";
import type { CalendarEvent, CalendarResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";

const KIND_STYLE: Record<CalendarEvent["kind"], string> = { bill: "bg-amber-500/15 text-amber-600 dark:text-amber-300", subscription: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-300", income: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300" };

function shiftMonth(key: string, delta: number) {
  const [y, m] = key.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return d.toISOString().slice(0, 7);
}

export default function CalendarPage() {
  const { t } = useT();
  const WEEKDAYS = [t("calendar.weekday.mon"), t("calendar.weekday.tue"), t("calendar.weekday.wed"), t("calendar.weekday.thu"), t("calendar.weekday.fri"), t("calendar.weekday.sat"), t("calendar.weekday.sun")];
  const KIND_LABEL: Record<CalendarEvent["kind"], string> = { bill: t("calendar.kind.bill"), subscription: t("calendar.kind.subscription"), income: t("calendar.kind.income") };
  const [month, setMonth] = useState(monthIso());
  const { data } = useQuery({ queryKey: ["calendar", month], queryFn: () => apiGet<CalendarResponse>(`/calendar?month=${month}`), retry: false });
  const { display } = useMoney();
  const [selected, setSelected] = useState<string | null>(null);

  const grid = useMemo(() => {
    const [y, m] = month.split("-").map(Number);
    const first = new Date(Date.UTC(y, m - 1, 1));
    const daysInMonth = new Date(Date.UTC(y, m, 0)).getUTCDate();
    const lead = (first.getUTCDay() + 6) % 7; // Monday-first
    const cells: (string | null)[] = Array.from({ length: lead }, () => null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(`${month}-${String(d).padStart(2, "0")}`);
    while (cells.length % 7) cells.push(null);
    return cells;
  }, [month]);

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    data?.events.forEach((e) => map.set(e.date, [...(map.get(e.date) ?? []), e]));
    return map;
  }, [data]);

  const todayKey = new Date().toISOString().slice(0, 10);
  const listed = selected ? (byDay.get(selected) ?? []) : (data?.events ?? []);

  return (
    <div data-testid="calendar-page">
      <PageHeader eyebrow={t("calendar.eyebrow")} title={t("calendar.title")} description={t("calendar.description")} testId="calendar-header"
        actions={<div className="flex items-center gap-1 rounded-lg border border-border bg-card p-1">
          <Button variant="ghost" size="icon-sm" onClick={() => { setMonth((m) => shiftMonth(m, -1)); setSelected(null); }} aria-label={t("calendar.prevMonth")} data-testid="calendar-prev-month"><ChevronLeft size={16} /></Button>
          <span className="min-w-32 text-center text-sm font-medium" data-testid="calendar-month-label">{data?.label ?? month}</span>
          <Button variant="ghost" size="icon-sm" onClick={() => { setMonth((m) => shiftMonth(m, 1)); setSelected(null); }} aria-label={t("calendar.nextMonth")} data-testid="calendar-next-month"><ChevronRight size={16} /></Button>
        </div>} />

      <section className="mb-6 grid gap-4 sm:grid-cols-3" data-testid="calendar-stats">
        <StatCard label={t("calendar.stat.out")} value={display(data?.total_out ?? 0)} detail={t("calendar.stat.outDetail")} icon={<ChevronRight size={17} />} tone="amber" testId="calendar-total-out" />
        <StatCard label={t("calendar.stat.in")} value={display(data?.total_in ?? 0)} detail={t("calendar.stat.inDetail")} icon={<ChevronLeft size={17} />} tone="emerald" testId="calendar-total-in" />
        <StatCard label={t("calendar.stat.days")} value={String([...byDay.keys()].filter((d) => byDay.get(d)?.some((e) => e.kind !== "income")).length)} detail={t("calendar.stat.daysDetail")} icon={<ChevronRight size={17} />} tone="cyan" testId="calendar-payment-days" />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Panel testId="calendar-grid-card">
          <div className="mb-2 grid grid-cols-7 text-center text-[11px] uppercase tracking-wider text-muted-foreground">{WEEKDAYS.map((d) => <span key={d}>{d}</span>)}</div>
          <div className="grid grid-cols-7 gap-1" data-testid="calendar-grid">
            {grid.map((day, index) => {
              if (!day) return <div key={`empty-${index}`} className="min-h-16 sm:min-h-24" />;
              const events = byDay.get(day) ?? [];
              const total = events.filter((e) => e.kind !== "income").reduce((s, e) => s + e.amount, 0);
              return (
                <button key={day} type="button" onClick={() => setSelected(selected === day ? null : day)} data-testid={`calendar-day-${day}`}
                  className={cn("flex min-h-16 flex-col rounded-lg border p-1.5 text-left transition-[border-color,background-color] sm:min-h-24", selected === day ? "border-primary bg-primary/10" : "border-border/60 hover:bg-accent", day === todayKey && "ring-1 ring-primary/60")}>
                  <span className={cn("text-xs", day === todayKey ? "font-bold text-primary" : "text-muted-foreground")}>{Number(day.slice(-2))}</span>
                  <div className="mt-1 hidden flex-1 space-y-0.5 sm:block">
                    {events.slice(0, 2).map((e) => <span key={`${e.kind}-${e.id}`} className={cn("block truncate rounded px-1 text-[10px]", KIND_STYLE[e.kind])}>{e.title}</span>)}
                    {events.length > 2 && <span className="block text-[10px] text-muted-foreground">+{events.length - 2}</span>}
                  </div>
                  {total > 0 && <span className="mt-auto font-mono text-[10px] font-semibold" data-testid={`calendar-day-total-${day}`}>{money(total)}</span>}
                  {events.length > 0 && <span className="mt-auto flex gap-0.5 sm:hidden">{events.slice(0, 3).map((e) => <span key={`${e.kind}-${e.id}`} className={cn("h-1.5 w-1.5 rounded-full", KIND_STYLE[e.kind])} />)}</span>}
                </button>
              );
            })}
          </div>
        </Panel>

        <Panel title={selected ? `${Number(selected.slice(-2))} ${data?.label ?? ""}` : t("calendar.throughMonth")} description={selected ? t("calendar.selectedDay") : t("calendar.allEvents")} testId="calendar-events-card"
          action={selected && <Button variant="ghost" size="sm" onClick={() => setSelected(null)} data-testid="calendar-clear-selection">{t("calendar.clearSelection")}</Button>}>
          {listed.length === 0 ? <p className="py-10 text-center text-sm text-muted-foreground" data-testid="calendar-events-empty">{t("calendar.noEvents")}</p> : (
            <ul className="divide-y divide-border">
              {listed.map((e) => (
                <li key={`${e.kind}-${e.id}-${e.date}`} className="flex items-center gap-3 py-2.5" data-testid={`calendar-event-${e.id}`}>
                  <span className="w-7 shrink-0 font-mono text-sm font-semibold text-muted-foreground">{Number(e.date.slice(-2))}</span>
                  <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", KIND_STYLE[e.kind])}>{KIND_LABEL[e.kind]}</span>
                  <p className="min-w-0 flex-1 truncate text-sm">{e.title}</p>
                  <p className={cn("font-mono text-sm font-semibold", e.kind === "income" && "text-emerald-500")}>{e.kind === "income" ? "+" : ""}{money(e.amount, e.currency, e.currency === "TRY" ? 0 : 2)}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
