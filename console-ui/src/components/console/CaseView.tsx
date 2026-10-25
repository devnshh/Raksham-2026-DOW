import { Copy } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Bar } from "@/components/charts/bar";
import { BarSparkline, LineSparkline } from "@/components/charts/sparkline";
import { BarChart } from "@/components/charts/bar-chart";
import { Gauge } from "@/components/charts/gauge";
import { Grid } from "@/components/charts/grid";
import { BarYAxis } from "@/components/charts/bar-y-axis";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { SankeyChart, SankeyLink, SankeyNode, SankeyTooltip } from "@/components/charts/sankey";
import { ChartTooltip } from "@/components/charts/tooltip";
import type { CaseRow, PayeeView, PayerAmounts, Summary } from "@/lib/api";
import { ago, CHANNEL, clock, EXPLAIN, FAMILY, HOT, holdEnd, hm, label, mmss, rupees, TIER, TIER_COLOR } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Caps, Panel, ScamBadge, Stat, StatusBadge, Tip, TierBadge } from "./ui";

export interface Detail { c: CaseRow; payee: PayeeView | null; amounts: PayerAmounts | null }
export interface CaseActions {
  release: () => void; acceptAppeal: () => void; confirm: (note: string) => void; clear: (note: string) => void;
  searchFor: (text: string, who: string) => void; select: (id: string) => void; copied: (id: string) => void;
}

const scorePct = (v: number) => (v <= 0.8 ? (v / 0.8) * 35 : 35 + ((v - 0.8) / 0.2) * 65);

export function CaseView({ detail, row, cases, summary, now, result, actions }: {
  detail: Detail; row: CaseRow; cases: CaseRow[]; summary: Summary | null; now: number;
  result: { text: string; err?: boolean } | null; actions: CaseActions;
}) {
  const { c, payee, amounts } = detail;
  const ev = c.evidence_pack ?? {}, f = ev.features ?? {};
  const cut = summary?.cutoffs ?? null;
  const score = typeof ev.score === "number" ? ev.score : null;
  const reports = payee?.reports ?? Number(f.payee_reports_prior ?? 0);
  const newPayers = payee?.new_payers_24h.length ?? Number(f.payee_new_payers_24h ?? 0);
  const ratio = amounts?.median ? c.amount / amounts.median : null;
  const thresholds = summary?.family_thresholds ?? {};
  const famUp = Object.keys(FAMILY).filter((k) => (ev.family_contrib?.[k] ?? 0) >= (thresholds[k] ?? 0.4));
  const signals = c.reasons.filter((r) => r !== "CHECK_UNAVAILABLE");
  const scamPayee = !!payee?.is_confirmed_scam || row.payee_confirmed_scam;
  const [note, setNote] = useState("");
  const holdLeft = row.hold_active ? holdEnd(c) - now : 0;
  // Tile sparklines: the payer's amounts ending on this payment, and money into the payee hour by hour.
  const amountTrail = [...(amounts?.payments ?? []).slice().reverse().map((p) => ({ v: p.amount })),
    ...(row.status === "completed" ? [] : [{ v: c.amount }])];
  const payeeHours = Array.from({ length: 24 }, (_, i) => ({
    v: (payee?.payments_24h ?? []).filter((t) => Math.floor((now - Date.parse(t)) / 3600e3) === 23 - i).length,
  }));
  const scoreTone = score == null ? "" : cut && score >= cut.red ? "red" : cut && score >= cut.amber ? "amber" : "green";

  return (
    <section className="animate-in fade-in slide-in-from-bottom-1 overflow-hidden rounded-xl border bg-card shadow-sm duration-300" aria-live="polite">
      {/* Header */}
      <div className="border-b border-[#eef0f4] bg-gradient-to-b from-[#fbfbfd] to-card px-5 pt-4 pb-3.5">
        <div className="flex items-center gap-2 text-[12.5px] text-muted-foreground">
          {scamPayee ? <ScamBadge /> : null}<TierBadge tier={c.tier} /><StatusBadge status={row.status} />
          <span>Case</span>
          <Tip text="Copy the case ID">
            <button type="button" onClick={() => { void navigator.clipboard?.writeText(c.case_id); actions.copied(c.case_id); }}
              className="inline-flex items-center gap-1 rounded-md border border-transparent px-1.5 font-mono text-xs text-[#475467] transition hover:border-border hover:bg-[#f6f7f9]">
              {c.case_id}<Copy className="size-3" />
            </button>
          </Tip>
          <span>{ago(c.created_at, now)} ago</span>
        </div>
        <div className="mt-1.5 flex items-center justify-between gap-4">
          <h2 className="flex min-w-0 flex-wrap items-baseline gap-x-2 text-[22px] leading-tight font-semibold tracking-[-.45px]">
            <span>{rupees(c.amount)} to</span>
            <LinkButton tip="Show every check to this payee" onClick={() => actions.searchFor(c.payee_vpa, "Payee")} className="text-lg">{c.payee_vpa}</LinkButton>
          </h2>
          <div className="flex shrink-0 flex-wrap justify-end gap-2">
            {row.hold_active && <Action tip="End the pause early after checking with the user. Their phone unlocks within seconds." onClick={actions.release}>Release hold</Action>}
            {row.dispute === "false_alarm_pending" && <Action tone="primary" tip="The warning was wrong: lower later checks for this user and payee" onClick={actions.acceptAppeal}>Accept appeal</Action>}
            {(scamPayee || (payee?.confirmations.length ?? 0) > 0) && <Action tip="Withdraw all confirmations for this payee" onClick={() => actions.clear(note)}>Clear payee</Action>}
            {!scamPayee && <Action tone="danger" tip="Two different analysts must confirm. Then every case to this UPI ID is marked as a scam." onClick={() => actions.confirm(note)}>Confirm scam</Action>}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-[22px] gap-y-1.5 text-[12.5px] text-[#475467]">
          <Fact k="Payer"><LinkButton tip="Show every check by this payer" onClick={() => actions.searchFor(c.user_ref, "Payer")} className="text-[12.5px]">{c.user_ref}</LinkButton></Fact>
          <Fact k="Entered by">{CHANNEL[String(f.entry_channel)] ?? String(f.entry_channel ?? "Unknown")}</Fact>
          <Fact k="Checked">{clock(c.created_at)} IST</Fact>
          <Fact k="Status">{row.status === "completed" ? "Paid" : row.status === "cancelled" ? (ev.cancelled_by_user ? "Cancelled by the user" : "Cancelled, reported as scam") : c.tier === "decline" ? "Blocked" : "Not paid"}</Fact>
        </div>
        {scamPayee && (
          <div className="mt-3 rounded-[10px] border border-[#ddcdf7] bg-[var(--risk-violet-soft)] px-3.5 py-2 text-[13px] font-medium text-[var(--risk-violet)]">
            Confirmed scam payee{payee?.confirmations.length ? ` (by ${payee.confirmations.join(" and ")})` : ""}: every case to this UPI ID is marked, and new payments are declined.
            {row.status === "completed" && c.tier !== "decline" ? " This payment was completed: flag it for recovery." : ""}
          </div>
        )}
        {c.tier === "red" && (
          <div className={cn("mt-3 grid grid-cols-[auto_1fr_auto] items-center gap-3.5 rounded-[10px] border px-3.5 py-2.5",
            row.hold_active ? "border-[var(--risk-red-line)] bg-[var(--risk-red-soft)]" : "border-border bg-[#f6f7f9]")}>
            <span className={cn("text-[13px] font-semibold", row.hold_active ? "text-[var(--risk-red-ink)]" : "text-[#475467]")}>
              {row.hold_active ? "Payment on hold" : row.status === "cancelled" ? "Payment cancelled on the phone" : ev.hold_released_by ? `Hold released by ${ev.hold_released_by}` : "Hold has ended"}
            </span>
            <span className="h-1.5 overflow-hidden rounded-full bg-[rgba(200,39,28,.14)]">
              <span className="block h-full origin-left rounded-full bg-[var(--risk-red)] transition-transform duration-1000 ease-linear"
                style={{ transform: `scaleX(${row.hold_active ? Math.max(0, Math.min(1, holdLeft / (c.hold_minutes * 60000))) : 0})` }} />
            </span>
            <span className="min-w-[54px] text-right text-[15px] font-semibold text-[var(--risk-red-ink)]">{row.hold_active ? mmss(holdLeft) : ""}</span>
          </div>
        )}
        {c.tier !== "green" && (
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note for the audit log (optional)" aria-label="Note for the audit log"
            className="mt-2.5 w-full rounded-lg border bg-card px-2.5 py-[7px] text-[12.5px] outline-none transition focus:border-primary focus:ring-[3px] focus:ring-primary/20" />
        )}
        {result && <div role="status" className={cn("mt-2.5 animate-in fade-in rounded-lg px-3 py-2 text-[12.5px]", result.err ? "bg-[var(--risk-red-soft)] text-[var(--risk-red-ink)]" : "bg-[#eef2fd] text-[#2f4fb8]")}>{result.text}</div>}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-2.5 border-b border-[#eef0f4] bg-[#fbfbfd] px-5 py-3.5">
        <Tile tone={scoreTone} name="Model score" value={score == null ? "n/a" : score.toFixed(3)}
          sub={score == null ? "check ran without the model" : !cut ? "" : score >= cut.red ? "above the red cut-off" : score >= cut.amber ? "in the amber band" : `${(cut.amber - score).toFixed(3)} below amber`}
          meter={score} tip="Fusion model output between 0 and 1" />
        <Tile tone={signals.length ? "red" : "green"} name="Warning signals" value={String(signals.length)} sub={signals.length ? signals.slice(0, 2).map(label).join(" · ") : "nothing fired"}
          tip={signals.length ? signals.map(label).join(", ") : "No warning signals"} />
        <Tile tone={reports || newPayers >= 5 ? "red" : ""} name="Payee risk" value={`${reports} report${reports === 1 ? "" : "s"}`} sub={`${newPayers} new payer${newPayers === 1 ? "" : "s"} in 24 h`}
          spark={payeeHours.some((h) => h.v) ? <BarSparkline data={payeeHours} dataKey="v" height={30} color={reports || newPayers >= 5 ? "#c8271c" : "#3e63dd"} barRadius={1.5} /> : null}
          tip="Scam reports, and how many people paid this account for the first time today" />
        <Tile tone={ratio && ratio >= 2 ? "amber" : ""} name="Amount vs usual" value={ratio ? `${ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)}×` : "first"}
          sub={amounts?.median ? `usual ${rupees(amounts.median)}` : "no history yet"}
          spark={amountTrail.length > 1 ? <LineSparkline data={amountTrail} dataKey="v" height={30} color={ratio && ratio >= 2 ? "#f0a020" : "#667085"} endDot strokeWidth={1.75} /> : null} tip="This payment divided by the payer's median amount" />
      </div>

      {/* Why | Decision */}
      <div className="grid grid-cols-2 border-b border-[#eef0f4] [&>*+*]:border-l [&>*+*]:border-[#eef0f4]">
        <Panel title={c.tier === "green" ? "Why it passed" : "Why it fired"} aside={famUp.length ? `${famUp.length} of 4 risk families fire` : "no risk family fires"}>
          <div className="mb-1 flex flex-wrap gap-1.5">
            {signals.length ? signals.map((r) => (
              <Tip key={r} text={EXPLAIN[r] ?? label(r)}>
                <span className={cn("inline-block rounded-full border px-2.5 py-[3px] text-xs font-medium",
                  HOT.has(r) ? "border-[var(--risk-red-line)] bg-[var(--risk-red-soft)] text-[var(--risk-red-ink)]" : "border-border bg-[#fbfbfd] text-[#475467]")}>{label(r)}</span>
              </Tip>
            )) : <span className="rounded-full border border-[#c4e6d0] bg-[var(--risk-green-soft)] px-2.5 py-[3px] text-xs font-medium text-[var(--risk-green-ink)]">No warning signals</span>}
          </div>
          <FamilyRadar contrib={ev.family_contrib ?? {}} thresholds={thresholds} />
        </Panel>
        <Panel title="Decision" aside={score != null ? "model score against the cut-offs" : undefined}>
          <p className="mb-1 text-[13px] text-[#475467]"><b className="font-semibold text-foreground">{TIER[c.tier]}</b> · {verdict(c.tier)}</p>
          {score != null ? (
            <>
              <div className="mx-auto w-full max-w-[230px]">
                <Gauge minWidth={180} value={Math.max(1, scorePct(score))} centerValue={score} defaultLabel="Model score" totalNotches={44} spacing={22}
                  inactiveFillOpacity={0.35} formatOptions={{ minimumFractionDigits: 3, maximumFractionDigits: 3 }}
                  activeFill={scoreTone === "red" ? "var(--risk-red)" : scoreTone === "amber" ? "var(--risk-amber)" : "var(--risk-green)"} />
              </div>
              {cut && <CutoffScale score={score} amber={cut.amber} red={cut.red} />}
            </>
          ) : <p className="text-[13px] text-muted-foreground">No model score was recorded for this check.</p>}
          {ev.applied_rules?.length ? (
            <div className="mt-3">
              <Caps>Policy path</Caps>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {ev.applied_rules.map((r, i) => (
                  <span key={r + i} className="rounded-[5px] border border-[#eef0f4] bg-[#f6f7f9] px-1.5 py-0.5 font-mono text-[11px] text-[#475467]">{i ? "→ " : ""}{r}</span>
                ))}
              </div>
            </div>
          ) : null}
        </Panel>
      </div>

      {/* Payee | Payer */}
      <div className="grid grid-cols-2 border-b border-[#eef0f4] [&>*+*]:border-l [&>*+*]:border-[#eef0f4]">
        <Panel title="Payee" aside={<span className="font-mono">{c.payee_vpa}</span>}>
          <div className="mb-3 grid grid-cols-3 gap-2">
            <Stat k="Account age" v={ev.payee_age_known ? `${Math.round(Number(f.payee_age_days))} days` : "Unknown"} flag={!!ev.payee_age_known && Number(f.payee_age_days) <= 30} tip="Accounts under 30 days old are a mule warning sign" />
            <Stat k="Reports" v={reports} flag={reports > 0} tip="From users who dealt with this payee, weighted by their history" />
            <Stat k="New payers 24 h" v={newPayers} flag={newPayers >= 5} tip="People paying this account for the first time in 24 hours" />
            <Stat k="Verified merchant" v={f.payee_verified ? "Yes" : "No"} tip="From the bank's merchant registry" />
            <Stat k="Brand look-alike" v={Number(f.lookalike_score ?? 0).toFixed(2)} flag={Number(f.lookalike_score) >= 0.7} tip="0.70 or more means the UPI ID imitates a brand or bank" />
            <Stat k="Analyst confirms" v={`${payee?.confirmations.length ?? 0} of 2`} flag={scamPayee} tip="Two different analysts decline the payee for everyone" />
          </div>
          <Caps>Payments in · 24 h, by 4-hour slot</Caps>
          <PayersPerHour payers={payee?.new_payers_24h ?? []} payments={payee?.payments_24h ?? []} now={now} />
        </Panel>
        <Panel title="Payer" aside={<span className="font-mono">{c.user_ref}</span>}>
          <div className="mb-3 grid grid-cols-3 gap-2">
            <Stat k="Usual amount" v={amounts?.median ? rupees(amounts.median) : "n/a"} tip="Median of the payer's recent completed payments" />
            <Stat k="This payment" v={rupees(c.amount)} flag={!!ratio && ratio >= 2} tip="At least twice the usual amount counts as unusual" />
            <Stat k="Largest before" v={amounts?.amounts.length ? rupees(Math.max(...amounts.amounts)) : "n/a"} tip="Largest of the recent completed payments" />
          </div>
          <Caps>{amounts?.payments.length ? `How much this payer usually sends · last ${amounts.payments.length} payments${row.status === "completed" ? "" : ", this one highlighted"}` : "No payment history yet"}</Caps>
          <PaymentHistory c={c} amounts={amounts} />
          <OtherChecks c={c} cases={cases} now={now} select={actions.select} />
        </Panel>
      </div>

      {/* Money flow */}
      {(payee?.new_payers_24h.length ?? 0) > 0 && (
        <div className="border-b border-[#eef0f4]">
          <Panel title="Money into this account · 24 h" aside="first-time payers on the left, this payee on the right">
            <MoneyFlow payee={c.payee_vpa} payers={payee!.new_payers_24h} />
          </Panel>
        </div>
      )}

      {/* Trail */}
      <Panel title="Case trail" aside={ev.audit?.sequence != null ? `audit entry #${ev.audit.sequence} · hash-chained` : undefined}>
        <Trail c={c} row={row} />
      </Panel>
    </section>
  );
}

function verdict(tier: string) {
  return tier === "red" ? "score above the red cut-off with two or more risk families" : tier === "amber" ? "warned once, the user can continue"
    : tier === "decline" ? "analysts confirmed this payee as a scam" : "nothing crossed a cut-off";
}

function Fact({ k, children }: { k: string; children: ReactNode }) {
  return <span className="inline-flex items-center"><b className="mr-1.5 font-medium text-muted-foreground">{k}</b>{children}</span>;
}

function LinkButton({ children, onClick, tip, className }: { children: ReactNode; onClick: () => void; tip: string; className?: string }) {
  return (
    <Tip text={tip}>
      <button type="button" onClick={onClick}
        className={cn("-mx-1 rounded-md px-1 font-mono font-medium text-foreground underline decoration-border underline-offset-4 transition hover:bg-[#eef2fd] hover:text-[#2f4fb8] hover:decoration-current", className)}>
        {children}
      </button>
    </Tip>
  );
}

function Action({ children, onClick, tip, tone }: { children: ReactNode; onClick: () => void; tip: string; tone?: "danger" | "primary" }) {
  const [busy, setBusy] = useState(false);
  return (
    <Tip text={tip} side="bottom">
      <button type="button" disabled={busy} onClick={async () => { setBusy(true); try { await onClick(); } finally { setBusy(false); } }}
        className={cn("rounded-[9px] border px-3.5 py-2 text-[13px] font-medium whitespace-nowrap shadow-sm transition active:translate-y-px disabled:opacity-60",
          tone === "danger" ? "border-[var(--risk-red)] bg-[var(--risk-red)] text-white hover:bg-[#b0221a]"
            : tone === "primary" ? "border-primary bg-primary text-white hover:bg-[#2f4fb8]" : "bg-card hover:bg-[#f6f7f9]")}>
        {children}
      </button>
    </Tip>
  );
}

function Tile({ tone, name, value, sub, meter, spark, tip }: { tone: string; name: string; value: string; sub: string; meter?: number | null; spark?: ReactNode; tip: string }) {
  const ink = tone === "red" ? "text-[var(--risk-red-ink)]" : tone === "amber" ? "text-[var(--risk-amber-ink)]" : tone === "green" ? "text-[var(--risk-green-ink)]" : "";
  const fill = tone === "red" ? "var(--risk-red)" : tone === "amber" ? "var(--risk-amber)" : "var(--risk-green)";
  return (
    <Tip text={tip} className="block min-w-0">
      <div className="min-w-0 rounded-[10px] border bg-card px-3 py-2.5 transition duration-200 hover:-translate-y-px hover:shadow-md">
        <Caps>{name}</Caps>
        <div className="flex items-end justify-between gap-2">
          <div className="min-w-0">
            <div className={cn("mt-0.5 truncate text-[19px] leading-tight font-semibold tracking-[-.35px]", ink)}>{value}</div>
            <div className="mt-0.5 truncate text-xs text-muted-foreground">{sub}</div>
          </div>
          {spark && <div className="h-[30px] w-[84px] shrink-0">{spark}</div>}
        </div>
        {meter != null && (
          <div className="mt-2 h-[5px] overflow-hidden rounded-full bg-[#eef0f4]">
            <div className="h-full origin-left animate-in slide-in-from-left rounded-full duration-700" style={{ width: `${Math.max(3, scorePct(meter))}%`, background: fill }} />
          </div>
        )}
      </div>
    </Tip>
  );
}

function CutoffScale({ score, amber, red }: { score: number; amber: number; red: number }) {
  const zones = [
    { from: 0, to: amber, color: "#ddf0e4", tip: `Green: below ${amber.toFixed(3)}, no warning from the model` },
    { from: amber, to: red, color: "#fdebc4", tip: `Amber: ${amber.toFixed(3)} to ${red.toFixed(3)}, a one-tap warning` },
    { from: red, to: 1, color: "#f9cfc9", tip: `Red: ${red.toFixed(3)} and above, a red pause when two risk families agree` },
  ];
  return (
    <div className="mt-2">
      <div className="relative flex h-2.5 rounded-full">
        {zones.map((z) => (
          <Tip key={z.tip} text={z.tip} className="block h-full" >
            <span className="block h-full first:rounded-l-full" style={{ width: `${scorePct(z.to) - scorePct(z.from)}%`, background: z.color, minWidth: 0 }} />
          </Tip>
        ))}
        <span className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[2.5px] border-white bg-foreground shadow transition-[left] duration-700" style={{ left: `${scorePct(score)}%` }} />
      </div>
      <div className="relative mt-1.5 h-4 text-[11px] text-muted-foreground">
        <span className="absolute left-0">0</span>
        <span className="absolute -translate-x-1/2" style={{ left: `${scorePct(0.8)}%` }}>0.8</span>
        <span className="absolute -translate-x-1/2" style={{ left: `${scorePct(amber)}%` }}>amber {amber.toFixed(3)}</span>
        <span className="absolute right-0">red {red.toFixed(3)}</span>
      </div>
    </div>
  );
}

function FamilyRadar({ contrib, thresholds }: { contrib: Record<string, number>; thresholds: Record<string, number> }) {
  const keys = Object.keys(FAMILY);
  const data = keys.map((k) => ({ family: FAMILY[k][0], "This check": Number((contrib[k] ?? 0).toFixed(2)), "Fires at": thresholds[k] ?? 0.4 }));
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_164px] items-center gap-3">
      <BarChart data={data} xDataKey="family" orientation="horizontal" aspectRatio="1.9 / 1" barGap={0.3}
        margin={{ top: 6, right: 12, bottom: 6, left: 84 }}>
        <Grid vertical />
        <Bar dataKey="Fires at" fill="#c3cad6" lineCap="round" />
        <Bar dataKey="This check" fill="var(--risk-red)" lineCap="round" />
        <BarYAxis />
        <ChartTooltip />
      </BarChart>
      <div className="space-y-1">
        {keys.map((k) => {
          const v = contrib[k] ?? 0, t = thresholds[k] ?? 0.4, up = v >= t;
          return (
            <Tip key={k} text={`${FAMILY[k][1]}. ${up ? "Fires" : "Does not fire"}: threshold ${t.toFixed(2)}.`} className="block">
              <div className="flex items-center justify-between rounded-md px-2 py-1 text-[12.5px] transition-colors hover:bg-[#f6f7f9]">
                <span className="flex items-center gap-1.5"><span className={cn("size-2 rounded-full", up ? "bg-[var(--risk-red)]" : "bg-[#c3cad6]")} />{FAMILY[k][0]}</span>
                <span className={cn("font-semibold", up ? "text-[var(--risk-red-ink)]" : "text-[#475467]")}>{v.toFixed(2)}</span>
              </div>
            </Tip>
          );
        })}
        <div className="flex items-center gap-3 px-2 pt-1 text-[11px] whitespace-nowrap text-muted-foreground">
          <span className="flex items-center gap-1"><i className="inline-block h-2 w-3 rounded-sm bg-[var(--risk-red)]" />this check</span>
          <span className="flex items-center gap-1"><i className="inline-block h-2 w-3 rounded-sm bg-[#c3cad6]" />fires at</span>
        </div>
      </div>
    </div>
  );
}

// Same pair as the Bklit bar-chart preview: indigo for all payments, gold for first-time payers.
const BAR_ALL = "var(--primary)";
const BAR_NEW = "var(--risk-amber)";
const SLOT_HOURS = 4;  // six 4-hour slots: hourly counts are mostly 0 or 1 and would draw hairline bars

function PayersPerHour({ payers, payments, now }: { payers: PayeeView["new_payers_24h"]; payments: string[]; now: number }) {
  const minute = Math.floor(now / 60000);  // re-bin once a minute, not every second
  const data = useMemo(() => {
    const at = minute * 60000, slots = 24 / SLOT_HOURS, span = SLOT_HOURS * 3600e3;
    const bins = Array.from({ length: slots }, (_, i) => {
      const start = at - (slots - i) * span;
      return { slot: `${hm(start).slice(0, 2)}–${hm(start + span).slice(0, 2)}`, "All payments": 0, "First-time payers": 0 };
    });
    const slot = (iso: string) => slots - 1 - Math.floor((at - new Date(iso).getTime()) / span);
    for (const t of payments) { const i = slot(t); if (i >= 0 && i < slots) bins[i]["All payments"] += 1; }
    for (const p of payers) { const i = slot(p.first_payment); if (i >= 0 && i < slots) bins[i]["First-time payers"] += 1; }
    return bins;
  }, [payers, payments, minute]);
  const latest = data.at(-1)?.["First-time payers"] ?? 0;
  return (
    <div className="mt-1.5">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-3 text-xs">
        <span className="flex items-center gap-3 text-muted-foreground">
          <span className="flex items-center gap-1.5"><i className="inline-block size-2 rounded-sm" style={{ background: BAR_ALL }} />{payments.length} payments</span>
          <span className="flex items-center gap-1.5"><i className="inline-block size-2 rounded-sm" style={{ background: BAR_NEW }} />{payers.length} first-time payers</span>
        </span>
        <span className={cn(latest >= 3 ? "font-medium text-[var(--risk-red-ink)]" : "text-muted-foreground")}>{latest} new in the last {SLOT_HOURS} h</span>
      </div>
      <BarChart data={data} xDataKey="slot" aspectRatio="2.4 / 1" margin={{ top: 12, right: 8, bottom: 34, left: 8 }} barGap={0.28}>
        <Grid horizontal />
        <Bar dataKey="All payments" fill={BAR_ALL} lineCap="round" />
        <Bar dataKey="First-time payers" fill={BAR_NEW} lineCap="round" />
        <BarXAxis />
        <ChartTooltip />
      </BarChart>
    </div>
  );
}

const BANDS: [string, number][] = [["Up to ₹500", 500], ["₹500–2k", 2000], ["₹2k–10k", 10000], ["₹10k–50k", 50000], ["₹50k+", Infinity]];

/** How often the payer paid in each amount range, with this payment stacked in its range. Counts, not
 *  amounts, so one big payment cannot flatten the rest: a red block in an empty range reads "never this much". */
function PaymentHistory({ c, amounts }: { c: CaseRow; amounts: PayerAmounts | null }) {
  const data = useMemo(() => {
    const band = (v: number) => BANDS.findIndex(([, top]) => v <= top);
    const rows: Record<string, string | number>[] = BANDS.map(([name]) => ({ band: name, "Past payments": 0 }));
    for (const p of amounts?.payments ?? []) (rows[band(p.amount)]["Past payments"] as number)++;
    // A completed case is already in the history; an open one is the payment being checked.
    if (c.status !== "completed") rows[band(c.amount)]["This payment"] = 1;
    return rows;
  }, [amounts, c.amount, c.status]);
  if (!amounts?.payments.length) return <div className="mt-2 h-[120px] rounded-lg border border-dashed text-center text-xs leading-[120px] text-muted-foreground">No completed payments yet</div>;
  return (
    <div className="mt-1">
      <BarChart data={data} xDataKey="band" stacked aspectRatio="3 / 1" margin={{ top: 10, right: 8, bottom: 34, left: 8 }} barGap={0.32}>
        <Grid horizontal />
        <Bar dataKey="Past payments" fill="var(--primary)" lineCap={3} />
        <Bar dataKey="This payment" fill={TIER_COLOR[c.tier]} lineCap={3} />
        <BarXAxis showAllLabels />
        <ChartTooltip />
      </BarChart>
    </div>
  );
}

function OtherChecks({ c, cases, now, select }: { c: CaseRow; cases: CaseRow[]; now: number; select: (id: string) => void }) {
  const others = cases.filter((x) => x.user_ref === c.user_ref && x.case_id !== c.case_id).slice(0, 4);
  if (!others.length) return null;
  return (
    <div className="mt-3">
      <Caps>Other checks by this payer</Caps>
      <div className="mt-1">
        {others.map((x) => (
          <button key={x.case_id} type="button" onClick={() => select(x.case_id)}
            className="-mx-2 grid w-[calc(100%+16px)] grid-cols-[auto_minmax(0,1fr)_auto_44px] items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-[12.5px] transition-colors hover:bg-[#f6f7f9]">
            <span className="flex items-center gap-1">{x.payee_confirmed_scam ? <ScamBadge /> : <TierBadge tier={x.tier} />}<StatusBadge status={x.status} /></span>
            <span className="truncate font-mono text-xs">{x.payee_vpa}</span>
            <span className="font-semibold">{rupees(x.amount)}</span>
            <span className="text-right text-[11.5px] text-muted-foreground">{ago(x.created_at, now)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function MoneyFlow({ payee, payers }: { payee: string; payers: PayeeView["new_payers_24h"] }) {
  const data = useMemo(() => {
    const top = payers.slice().sort((a, b) => b.total - a.total);
    const shown = top.slice(0, 7), rest = top.slice(7);
    const nodes = [...shown.map((p) => ({ name: p.payer_id, category: "source" as const })), ...(rest.length ? [{ name: `${rest.length} more payers`, category: "source" as const }] : []), { name: payee, category: "outcome" as const }];
    const target = nodes.length - 1;
    const links = [
      ...shown.map((p, i) => ({ source: i, target, value: Math.max(1, p.total) })),
      ...(rest.length ? [{ source: shown.length, target, value: Math.max(1, rest.reduce((s, p) => s + p.total, 0)) }] : []),
    ];
    return { nodes, links };
  }, [payee, payers]);
  return (
    <SankeyChart data={data} aspectRatio="3.2 / 1" margin={{ top: 12, right: 200, bottom: 12, left: 240 }} nodePadding={10} nodeWidth={12}>
      <SankeyLink />
      <SankeyNode lineCap={3} formatValue={(v) => rupees(v)} />
      <SankeyTooltip formatValue={(v) => rupees(v)} />
    </SankeyChart>
  );
}

function Trail({ c, row }: { c: CaseRow; row: CaseRow }) {
  const ev = c.evidence_pack ?? {};
  const steps: [string, string | null, "ok" | "red" | "next" | ""][] = [["Risk check from the phone", c.created_at, "ok"]];
  if (c.tier !== "green") steps.push([`${TIER[c.tier]} shown${c.tier === "red" ? `, ${c.hold_minutes}-min hold` : ""}`, c.created_at, c.tier === "red" || c.tier === "decline" ? "red" : ""]);
  if (ev.dispute === "this_was_me") steps.push(["User tapped “This was me”", null, ""]);
  if (ev.dispute === "false_alarm_pending") steps.push(["User reported a false alarm", null, ""]);
  if (ev.appeal_accepted_by) steps.push([`Appeal accepted by ${ev.appeal_accepted_by}`, null, "ok"]);
  if (ev.hold_released_by) steps.push([`Hold released by ${ev.hold_released_by}`, ev.hold_released_at ?? null, "ok"]);
  if (ev.cancelled) steps.push(["Cancelled and reported as a scam", null, "red"]);
  else if (ev.cancelled_by_user) steps.push(["User cancelled the payment", null, "ok"]);
  if (ev.completed) steps.push(["Payment completed", ev.completed_at ?? null, "ok"]);
  if (row.payee_confirmed_scam) steps.push(["Payee confirmed as a scam", null, "red"]);
  if (row.hold_active) steps.push(["Hold ends", new Date(holdEnd(c)).toISOString(), "next"]);
  return (
    <div className="flex overflow-x-auto">
      {steps.map(([what, t, tone], i) => (
        <Tip key={what + i} text={t ? new Date(t).toLocaleString("en-IN") : "Time not recorded"} className="relative block min-w-[150px] flex-1 pr-3">
          {i < steps.length - 1 && <span className="absolute top-1.5 right-0 left-3.5 h-0.5 bg-border" />}
          <span className={cn("relative z-10 block size-3.5 rounded-full border-2 bg-card",
            tone === "ok" ? "border-[var(--risk-green)]" : tone === "red" ? "border-[var(--risk-red)] bg-[var(--risk-red)]" : tone === "next" ? "border-dashed border-[#98a2b3]" : "border-[#98a2b3]")} />
          <span className="mt-2 block text-[13px] font-medium">{what}</span>
          <span className="mt-0.5 block text-[11.5px] text-muted-foreground">{t ? `${clock(t)} IST` : "time not recorded"}</span>
        </Tip>
      ))}
    </div>
  );
}
