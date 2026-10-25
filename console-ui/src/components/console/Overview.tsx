import { useMemo, type ReactNode } from "react";
import { AreaSparkline, BarSparkline, useSparklineHover } from "@/components/charts/sparkline";
import { LiveLineChart } from "@/components/charts/live-line-chart";
import { LiveLine } from "@/components/charts/live-line";
import { LiveXAxis } from "@/components/charts/live-x-axis";
import { RingChart } from "@/components/charts/ring-chart";
import { Ring } from "@/components/charts/ring";
import { RingCenter } from "@/components/charts/ring-center";
import { Bar } from "@/components/charts/bar";
import { BarChart } from "@/components/charts/bar-chart";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { BarYAxis } from "@/components/charts/bar-y-axis";
import { Grid } from "@/components/charts/grid";
import { SankeyChart, SankeyLink, SankeyNode, SankeyTooltip } from "@/components/charts/sankey";
import { ChartTooltip } from "@/components/charts/tooltip";
import type { CaseRow, Summary } from "@/lib/api";
import { compactRupees, hm, label, rupees, TIER_COLOR } from "@/lib/format";
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

/* ---------- Insights: the last 24 hours seen four ways ---------- */
const HEX = { green: "#2f9e5b", amber: "#f0a020", red: "#c8271c", decline: "#6b30c2" };

function Card({ title, aside, children, className }: { title: string; aside?: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("min-w-0 rounded-xl border bg-card px-4 pt-3 pb-3 shadow-sm", className)}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h3 className="text-[13.5px] font-semibold">{title}</h3>
        {aside && <span className="truncate text-xs text-muted-foreground">{aside}</span>}
      </div>
      {children}
    </div>
  );
}

const outcome = (c: CaseRow) => c.status === "completed" ? "Paid" : c.status === "cancelled" ? "Cancelled"
  : c.tier === "decline" ? "Blocked" : c.hold_active ? "On hold" : "Not paid";
const OUTCOME_HEX: Record<string, string> = { Paid: "#667085", Cancelled: "#2f9e5b", Blocked: "#6b30c2", "On hold": "#c8271c", "Not paid": "#c3cad6" };

export function Insights({ cases, summary, setTierFilter, search }: {
  cases: CaseRow[]; summary: Summary; setTierFilter: (f: TierFilter | null) => void; search: (q: string) => void;
}) {
  const day = useMemo(() => cases.filter((c) => Date.now() - Date.parse(c.created_at) < 24 * 3600e3), [cases]);

  // Tier mix per hour, from the server's own counts (not capped by the case list).
  const hours = useMemo(() => summary.hourly.map((h) => ({
    hour: hm(h.hour_start),
    Passed: Math.max(0, h.checks - h.warnings - h.decline), Amber: h.warnings - h.red, "Red pause": h.red, Declined: h.decline,
  })), [summary.hourly]);

  const reasons = useMemo(() => {
    const n = new Map<string, number>();
    for (const c of day) for (const r of c.reasons) if (r !== "CHECK_UNAVAILABLE") n.set(r, (n.get(r) ?? 0) + 1);
    return [...n].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([r, v]) => ({ reason: label(r), Checks: v }));
  }, [day]);

  // Risk checks, split by decision, then by what happened to the payment.
  const flow = useMemo(() => {
    const tiers = [["green", "Passed"], ["amber", "Amber"], ["red", "Red pause"], ["decline", "Declined"]] as const;
    const nodes: { name: string; category: "source" | "landing" | "outcome"; color: string }[] = [{ name: "Risk checks", category: "source", color: "#3e63dd" }];
    const links: { source: number; target: number; value: number }[] = [];
    const pairs: [number, string, number][] = [];
    for (const [tier, name] of tiers) {
      const group = day.filter((c) => c.tier === tier);
      if (!group.length) continue;
      const ti = nodes.push({ name, category: "landing", color: HEX[tier] }) - 1;
      links.push({ source: 0, target: ti, value: group.length });
      const by = new Map<string, number>();
      for (const c of group) by.set(outcome(c), (by.get(outcome(c)) ?? 0) + 1);
      for (const [o, v] of by) pairs.push([ti, o, v]);
    }
    // Outcome nodes go after every decision node, so the chart reads left to right.
    const outIdx = new Map<string, number>();
    for (const [, o] of pairs) if (!outIdx.has(o)) outIdx.set(o, nodes.push({ name: o, category: "outcome", color: OUTCOME_HEX[o] }) - 1);
    for (const [ti, o, v] of pairs) links.push({ source: ti, target: outIdx.get(o)!, value: v });
    return { nodes, links };
  }, [day]);

  const payees = useMemo(() => {
    const m = new Map<string, { vpa: string; held: number; pauses: number; scam: boolean }>();
    for (const c of day) {
      if (c.tier !== "red" && c.tier !== "decline") continue;
      const p = m.get(c.payee_vpa) ?? { vpa: c.payee_vpa, held: 0, pauses: 0, scam: false };
      p.pauses++; p.scam ||= c.payee_confirmed_scam;
      if (c.status !== "completed") p.held += c.amount;
      m.set(c.payee_vpa, p);
    }
    return [...m.values()].sort((a, b) => b.held - a.held).slice(0, 6);
  }, [day]);
  const maxHeld = Math.max(1, ...payees.map((p) => p.held));

  return (
    <>
      <section className="mb-4 grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-3">
        <Card title="Decisions by hour" aside="last 12 h">
          <BarChart data={hours} xDataKey="hour" stacked aspectRatio="2.6 / 1" margin={{ top: 8, right: 8, bottom: 34, left: 8 }} barGap={0.3}>
            <Grid horizontal />
            <Bar dataKey="Passed" fill={HEX.green} lineCap={2} />
            <Bar dataKey="Amber" fill={HEX.amber} lineCap={2} />
            <Bar dataKey="Red pause" fill={HEX.red} lineCap={2} />
            <Bar dataKey="Declined" fill={HEX.decline} lineCap={2} />
            <BarXAxis maxLabels={6} />
            <ChartTooltip />
          </BarChart>
        </Card>
        <Card title="Why checks fired" aside={`${day.length} checks today`}>
          {reasons.length ? (
            <BarChart data={reasons} xDataKey="reason" orientation="horizontal" aspectRatio="1.9 / 1" barGap={0.32} margin={{ top: 4, right: 12, bottom: 4, left: 138 }}>
              <Grid vertical />
              <Bar dataKey="Checks" fill="var(--primary)" lineCap="round" />
              <BarYAxis labelWidth={130} />
              <ChartTooltip />
            </BarChart>
          ) : <Empty text="No warning signals today" />}
        </Card>
      </section>
      <section className="mb-4 grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-3">
        <Card title="From check to outcome" aside="what happened to each payment today">
          {day.length ? (
            <SankeyChart data={flow} aspectRatio="2.6 / 1" margin={{ top: 10, right: 110, bottom: 10, left: 100 }} nodePadding={14} nodeWidth={12}>
              <SankeyLink getNodeColor={(n) => String(n.color)} />
              <SankeyNode lineCap={3} getNodeColor={(n) => String(n.color)} formatValue={(v) => `${v} check${v === 1 ? "" : "s"}`} />
              <SankeyTooltip formatValue={(v) => `${v} check${v === 1 ? "" : "s"}`} />
            </SankeyChart>
          ) : <Empty text="No checks today" />}
        </Card>
        <Card title="Payees stopped most" aside="money not paid">
          {payees.length ? (
            <div className="space-y-1">
              {payees.map((p) => (
                <button key={p.vpa} type="button" onClick={() => search(p.vpa)}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-[#f6f7f9]">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="truncate font-mono text-[12.5px]">{p.vpa}</span>
                    {p.scam && <span className="shrink-0 rounded bg-[var(--risk-violet)] px-1.5 text-[10px] font-semibold uppercase tracking-[.4px] text-white">Scam</span>}
                  </span>
                  <span className="text-right text-[13px] font-semibold">{rupees(p.held)}</span>
                  <span className="h-1.5 overflow-hidden rounded-full bg-[#eef0f4]">
                    <span className="block h-full rounded-full" style={{ width: `${Math.max(3, (100 * p.held) / maxHeld)}%`, background: p.scam ? HEX.decline : HEX.red }} />
                  </span>
                  <span className="text-right text-[11.5px] text-muted-foreground">{p.pauses} stop{p.pauses === 1 ? "" : "s"}</span>
                </button>
              ))}
            </div>
          ) : <Empty text="Nothing stopped today" />}
          <button type="button" onClick={() => setTierFilter({ name: "red pauses and declines", tiers: ["red", "decline"] })}
            className="mt-2 px-2 text-xs font-medium text-primary">Show all stopped payments</button>
        </Card>
      </section>
    </>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="grid h-[150px] place-items-center rounded-lg border border-dashed text-xs text-muted-foreground">{text}</div>;
}
