import { useMemo } from "react";
import { AreaSparkline, BarSparkline, useSparklineHover } from "@/components/charts/sparkline";
import { LiveLineChart } from "@/components/charts/live-line-chart";
import { LiveLine } from "@/components/charts/live-line";
import { LiveXAxis } from "@/components/charts/live-x-axis";
import { RingChart } from "@/components/charts/ring-chart";
import { Ring } from "@/components/charts/ring";
import { RingCenter } from "@/components/charts/ring-center";
import type { CaseRow, Summary } from "@/lib/api";
import { compactRupees, hm, TIER_COLOR } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { TierFilter } from "./Sidebar";
import { Caps, Tip } from "./ui";

type Hour = Summary["hourly"][number];
const FILTERS: Record<string, TierFilter | null> = {
  checks: null, warn: { name: "warnings", tiers: ["amber", "red"] }, red: { name: "red pauses", tiers: ["red"] },
  dec: { name: "declines", tiers: ["decline"] }, held: { name: "red pauses and declines", tiers: ["red", "decline"] },
};

function Metric({ id, name, value, sub, series, color, ink, bars, active, onPick }: {
  id: string; name: string; value: string; sub: string; series?: { field: keyof Hour; rows: Hour[] }; color: string; ink?: string;
  bars?: boolean; active: boolean; onPick: (id: string) => void;
}) {
  const hover = useSparklineHover<Hour>();
  const shown = hover.datum;
  return (
    <button type="button" onClick={() => onPick(id)}
      className={cn("grid min-w-0 grid-cols-[minmax(0,1fr)_84px] items-end gap-x-2 rounded-xl border bg-card px-3.5 pt-3 pb-2.5 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-lg",
        active && "border-primary ring-[3px] ring-primary/20")}>
      <Caps className="col-span-2 truncate">{name}</Caps>
      <div className="mt-1 truncate text-[25px] leading-tight font-semibold tracking-[-.6px]" style={{ color: ink }}>
        {shown && series ? String(shown[series.field]) : value}
      </div>
      <div className="h-8">
        {series && (bars
          ? <BarSparkline data={series.rows} dataKey={series.field} height={32} color={color} barRadius={2} {...hover.sparklineProps} />
          : <AreaSparkline data={series.rows} dataKey={series.field} height={32} color={color} fill="gradient" {...hover.sparklineProps} />)}
      </div>
      <div className="col-span-2 mt-0.5 truncate text-xs text-muted-foreground">
        {shown && series ? `${hm(shown.hour_start)}–${hm(new Date(shown.hour_start).getTime() + 3600e3)}` : sub}
      </div>
    </button>
  );
}

export function Metrics({ summary, tierFilter, setTierFilter }: { summary: Summary; tierFilter: TierFilter | null; setTierFilter: (f: TierFilter | null) => void }) {
  const t = summary.totals, rows = summary.hourly;
  const pick = (id: string) => { const f = FILTERS[id]; setTierFilter(f && tierFilter?.name !== f.name ? f : null); };
  const on = (id: string) => !!tierFilter && FILTERS[id]?.name === tierFilter.name;
  return (
    <section className="mb-4 grid grid-cols-5 gap-3" aria-label="Last 24 hours">
      <Metric id="checks" name="Risk checks" value={t.checks.toLocaleString("en-IN")} sub={`last ${summary.hours} h · ${t.payers} phone${t.payers === 1 ? "" : "s"}`}
        series={{ field: "checks", rows }} color="#667085" active={false} onPick={pick} />
      <Metric id="warn" name="Warnings" value={String(t.warnings)} sub={t.checks ? `${Math.round((100 * t.warnings) / t.checks)}% of checks` : "none yet"}
        series={{ field: "warnings", rows }} color="#f0a020" active={on("warn")} onPick={pick} />
      <Metric id="red" name="Red pauses" value={String(t.red)} sub={`${t.holds_running} hold${t.holds_running === 1 ? "" : "s"} running`}
        series={{ field: "red", rows }} color="#c8271c" ink="var(--risk-red)" bars active={on("red")} onPick={pick} />
      <Metric id="dec" name="Declined" value={String(t.decline)} sub={t.disputes_pending ? `${t.disputes_pending} disputed` : "confirmed scam payees"}
        color="#6b30c2" ink="var(--risk-violet)" active={on("dec")} onPick={pick} />
      <Metric id="held" name="Money held back" value={compactRupees(Math.round(t.money_held))} sub="stopped before payment" color="#3e63dd" active={on("held")} onPick={pick} />
    </section>
  );
}

/** Live activity: checks in the last five minutes as they stream in, and today's decisions. */
export function Activity({ cases, summary, points, setTierFilter }: {
  cases: CaseRow[]; summary: Summary; points: { time: number; value: number }[]; setTierFilter: (f: TierFilter | null) => void;
}) {
  const t = summary.totals;
  const ring = useMemo(() => {
    const max = Math.max(1, t.checks);
    return [
      { label: "Passed", value: t.green, maxValue: max, color: TIER_COLOR.green, tiers: ["green"], name: "passed checks" },
      { label: "Amber", value: t.amber, maxValue: max, color: TIER_COLOR.amber, tiers: ["amber"], name: "ambers" },
      { label: "Red pause", value: t.red, maxValue: max, color: TIER_COLOR.red, tiers: ["red"], name: "red pauses" },
      { label: "Declined", value: t.decline, maxValue: max, color: TIER_COLOR.decline, tiers: ["decline"], name: "declines" },
    ];
  }, [t.checks, t.green, t.amber, t.red, t.decline]);
  const last = points.at(-1)?.value ?? 0;
  const recent = cases.filter((c) => Date.now() - new Date(c.created_at).getTime() < 300e3).length;
  return (
    <section className="mb-4 grid grid-cols-[minmax(0,1fr)_320px] gap-3">
      <div className="rounded-xl border bg-card px-4 pt-3 pb-2 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="relative grid size-2 place-items-center"><span className="absolute inset-0 animate-ping rounded-full bg-[var(--risk-green)] opacity-60" /><span className="size-2 rounded-full bg-[var(--risk-green)]" /></span>
            <h3 className="text-[13.5px] font-semibold">Live from phones</h3>
          </div>
          <Tip text="Risk checks that arrived in the last five minutes. Each payment on a phone moves the line within two seconds." side="bottom">
            <span className="text-xs text-muted-foreground">{recent} check{recent === 1 ? "" : "s"} in the last 5 min</span>
          </Tip>
        </div>
        <div className="relative h-[150px] overflow-hidden">
          <LiveLineChart data={points} value={last} window={300} margin={{ top: 18, right: 16, bottom: 26, left: 16 }} style={{ height: 150 }}>
            <LiveLine dataKey="value" stroke="var(--chart-line-primary)" formatValue={(v: number) => `${Math.round(v)} checks`} />
            <LiveXAxis />
          </LiveLineChart>
        </div>
      </div>
      <div className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 shadow-sm">
        <div className="w-[150px] shrink-0">
          <RingChart data={ring} size={150} strokeWidth={9} ringGap={4} baseInnerRadius={34}>
            {ring.map((r, i) => <Ring key={r.label} index={i} />)}
            <RingCenter defaultLabel="Checks" />
          </RingChart>
        </div>
        <div className="min-w-0 flex-1">
          <Caps className="mb-1.5">Today's decisions</Caps>
          {ring.map((r) => (
            <button key={r.label} type="button" onClick={() => setTierFilter({ name: r.name, tiers: r.tiers })}
              className="flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left text-[12.5px] transition-colors hover:bg-[#f6f7f9]">
              <span className="size-2 rounded-full" style={{ background: r.color }} />
              <span className="flex-1 text-[#475467]">{r.label}</span>
              <span className="font-semibold">{r.value}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
