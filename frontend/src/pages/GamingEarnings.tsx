import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Coins, Download, ShoppingBag, TrendingUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "@/lib/api";
import { money } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { GamingEarningsTrend } from "@/lib/types";
import { PageHeader, Panel, StatCard } from "@/components/shared/ui-bits";
import { Button } from "@/components/ui/button";

export default function GamingEarnings() {
  const { t } = useT();
  const RANGE_OPTIONS: { months: number; label: string }[] = [
    { months: 1, label: t("gamingEarnings.range.1") },
    { months: 3, label: t("gamingEarnings.range.3") },
    { months: 6, label: t("gamingEarnings.range.6") },
    { months: 12, label: t("gamingEarnings.range.12") },
  ];
  const [months, setMonths] = useState<number>(6);
  const trend = useQuery({ queryKey: ["gaming", "earnings-trend", months], queryFn: () => apiGet<GamingEarningsTrend>(`/gaming/earnings/trend?months=${months}`), staleTime: 60_000 });

  const commissionRateAvg = useMemo(() => {
    if (!trend.data || trend.data.total_spent === 0) return 0;
    return (trend.data.total_commission / trend.data.total_spent) * 100;
  }, [trend.data]);

  function exportCsv() {
    if (!trend.data) return;
    const rows: string[] = ["type,month,seller_id,seller_name,total_spent,commission,count"];
    trend.data.points.forEach((p) => {
      rows.push(`month,${p.month},,,${p.total_spent.toFixed(2)},${p.total_commission.toFixed(2)},${p.count}`);
    });
    trend.data.by_seller.forEach((s) => {
      rows.push(`seller,,${s.seller_id},"${s.seller_name}",${s.total_spent.toFixed(2)},${s.commission.toFixed(2)},${s.count}`);
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `subly-gaming-kazanc-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(t("gamingEarnings.csvDownloaded"));
  }

  if (trend.isLoading) return <div className="grid min-h-[50svh] place-items-center text-sm text-muted-foreground" data-testid="gaming-earnings-loading">{t("gamingEarnings.loading")}</div>;
  if (trend.error || !trend.data) return <div className="grid min-h-[50svh] place-items-center text-sm text-rose-500" data-testid="gaming-earnings-error">{t("gamingEarnings.loadError")}</div>;
  const d = trend.data;
  const empty = d.count === 0;

  return (
    <div className="space-y-6" data-testid="gaming-earnings-page">
      <Link to="/gaming" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-testid="gaming-earnings-back">
        <ArrowLeft size={13} /> {t("gamingGame.back")}
      </Link>

      <PageHeader
        eyebrow={t("gamingEarnings.eyebrow")}
        title={t("gamingEarnings.title")}
        description={t("gamingEarnings.description")}
        testId="gaming-earnings-header"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex overflow-hidden rounded-full border border-border bg-card" data-testid="gaming-earnings-range">
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt.months}
                  type="button"
                  onClick={() => setMonths(opt.months)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${months === opt.months ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
                  data-testid={`gaming-earnings-range-${opt.months}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <Button variant="outline" onClick={exportCsv} disabled={empty} data-testid="gaming-earnings-csv">
              <Download size={13} /> {t("gamingEarnings.downloadCsv")}
            </Button>
          </div>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-testid="gaming-earnings-kpis">
        <StatCard label={t("gamingEarnings.stat.totalEarnings")} value={money(d.total_commission, "TRY", 2)} detail={t("gamingEarnings.stat.lastMonths", { count: d.months })} icon={<Coins size={17} />} tone="emerald" testId="gaming-earnings-total-commission" />
        <StatCard label={t("gamingEarnings.stat.totalSpent")} value={money(d.total_spent, "TRY", 0)} detail={t("gamingEarnings.stat.purchaseCount", { count: d.count })} icon={<ShoppingBag size={17} />} tone="cyan" testId="gaming-earnings-total-spent" />
        <StatCard label={t("gamingEarnings.stat.avgCommission")} value={`%${commissionRateAvg.toFixed(2)}`} detail={t("gamingEarnings.stat.perSpend")} icon={<TrendingUp size={17} />} tone="indigo" testId="gaming-earnings-avg-rate" />
        <StatCard label={t("gamingEarnings.stat.activeMonths")} value={String(d.points.filter((p) => p.count > 0).length)} detail={`${d.range_from} → ${d.range_to}`} icon={<Coins size={17} />} tone="amber" testId="gaming-earnings-active-months" />
      </section>

      <Panel title={t("gamingEarnings.trend.title")} description={t("gamingEarnings.trend.description", { count: d.months })} testId="gaming-earnings-trend-panel">
        {empty ? (
          <p className="py-10 text-center text-sm text-muted-foreground" data-testid="gaming-earnings-empty">
            {t("gamingEarnings.trend.empty", { count: d.months })}
          </p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d.points} barGap={4} barCategoryGap="28%">
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="month_label" tickLine={false} axisLine={false} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                <YAxis tickLine={false} axisLine={false} width={44} tick={{ fill: "var(--muted-foreground)", fontSize: 10 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                <Tooltip
                  cursor={{ fill: "var(--accent)", opacity: 0.4 }}
                  contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }}
                  formatter={(value: number, name: string) => [money(value, "TRY", 2), name === "total_spent" ? t("gamingEarnings.chart.spend") : t("gamingEarnings.chart.commission")]}
                />
                <Bar dataKey="total_spent" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
                <Bar dataKey="total_commission" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Panel>

      <Panel title={t("gamingEarnings.bySeller.title")} description={t("gamingEarnings.bySeller.description")} testId="gaming-earnings-sellers">
        {d.by_seller.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="gaming-earnings-sellers-empty">{t("gamingEarnings.bySeller.empty")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="gaming-earnings-seller-table">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                  <th className="py-2">{t("gamingEarnings.table.seller")}</th>
                  <th className="py-2 text-right">{t("gamingEarnings.table.transactions")}</th>
                  <th className="py-2 text-right">{t("gamingEarnings.table.spend")}</th>
                  <th className="py-2 text-right">{t("gamingEarnings.table.commission")}</th>
                  <th className="py-2 text-right">{t("gamingEarnings.table.rate")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.by_seller.map((row) => {
                  const rate = row.total_spent > 0 ? (row.commission / row.total_spent) * 100 : 0;
                  return (
                    <tr key={row.seller_id} data-testid={`gaming-earnings-seller-${row.seller_id}`}>
                      <td className="py-2">{row.seller_name}</td>
                      <td className="py-2 text-right font-mono text-xs text-muted-foreground">{row.count}</td>
                      <td className="py-2 text-right font-mono text-xs">{money(row.total_spent, "TRY", 2)}</td>
                      <td className="py-2 text-right font-mono text-sm font-semibold text-emerald-500">+{money(row.commission, "TRY", 2)}</td>
                      <td className="py-2 text-right font-mono text-xs text-muted-foreground">%{rate.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <p className="text-[11px] leading-relaxed text-muted-foreground" data-testid="gaming-earnings-note">
        {t("gamingEarnings.footnote")}
      </p>
    </div>
  );
}
