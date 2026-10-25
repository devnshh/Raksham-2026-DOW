import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CaseView, type Detail } from "@/components/console/CaseView";
import { Activity, Metrics } from "@/components/console/Overview";
import { Sidebar, type TierFilter, type View } from "@/components/console/Sidebar";
import { Toaster, useToast } from "@/components/console/ui";
import { api, getKey, setKey, Unauthorized, type CaseRow, type PayeeView, type PayerAmounts, type Summary } from "@/lib/api";
import { clock, disputed, needsAction, rupees, TIER } from "@/lib/format";
import { cn } from "@/lib/utils";

const RANK: Record<string, number> = { decline: 0, red: 1, amber: 2, green: 3 };
const ANALYST = "satark.analyst";

export default function App() {
  return <Toaster><Console /></Toaster>;
}

function Console() {
  const toast = useToast();
  const [needKey, setNeedKey] = useState(!getKey());
  const [keyError, setKeyError] = useState("");
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [connected, setConnected] = useState(false);
  const [updated, setUpdated] = useState("");
  const [view, setView] = useState<View>("action");
  const [query, setQuery] = useState("");
  const [tierFilter, setTierFilter] = useState<TierFilter | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [result, setResult] = useState<{ id: string; text: string; err?: boolean } | null>(null);
  const [analyst, setAnalyst] = useState(() => { try { return localStorage.getItem(ANALYST) || ""; } catch { return ""; } });
  const [now, setNow] = useState(Date.now());
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const [points, setPoints] = useState<{ time: number; value: number }[]>([]);
  const seen = useRef<Set<string> | null>(null);
  const lastPick = useRef(0);
  const selectedRef = useRef("");
  selectedRef.current = selectedId;

  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const c = await api<CaseRow>(`/v1/cases/${encodeURIComponent(id)}`);
      const [payee, amounts] = await Promise.all([
        api<PayeeView>(`/v1/payees/${encodeURIComponent(c.payee_vpa)}`).catch(() => null),
        api<PayerAmounts>(`/v1/users/${encodeURIComponent(c.user_ref)}/amounts`).catch(() => null)]);
      if (selectedRef.current === id) setDetail({ c, payee, amounts });
    } catch { /* the next poll retries */ }
  }, []);

  const select = useCallback((id: string, byUser = true) => {
    if (byUser) lastPick.current = Date.now();
    if (id === selectedRef.current) return;
    setSelectedId(id); setDetail(null); setResult(null);
    selectedRef.current = id;
    void loadDetail(id);
  }, [loadDetail]);

  const refresh = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([api<CaseRow[]>("/v1/cases?limit=100"), api<Summary>("/v1/console/summary")]);
      const first = seen.current === null;
      const known = seen.current ?? new Set<string>();
      const arrived = first ? [] : list.filter((c) => !known.has(c.case_id));
      seen.current = new Set([...known, ...list.map((c) => c.case_id)]);
      setCases(list); setSummary(sum); setConnected(true); setUpdated(`updated ${clock(Date.now())}`);
      const t = Date.now();
      setPoints((p) => [...p.slice(-400), { time: t / 1000, value: list.filter((c) => t - new Date(c.created_at).getTime() < 300e3).length }]);
      if (arrived.length) {
        setFresh(new Set(arrived.map((c) => c.case_id)));
        setTimeout(() => setFresh(new Set()), 3000);
      }
      const alarming = arrived.filter((c) => c.tier === "red" || c.tier === "decline");
      for (const c of alarming) {
        toast({ kind: c.tier === "decline" ? "decline" : "alert", title: `${TIER[c.tier]} · ${rupees(c.amount)}`, body: `${c.user_ref} → ${c.payee_vpa}`, onClick: () => select(c.case_id) });
      }
      // A new red pause or decline opens on its own unless the analyst picked a case in the last 20 s.
      if (alarming.length && Date.now() - lastPick.current > 20000) select(alarming[0].case_id, false);
      else if (first && !selectedRef.current && list.length) select((list.find((c) => needsAction(c)) ?? list[0]).case_id, false);
      else if (selectedRef.current) void loadDetail(selectedRef.current);
    } catch (e) {
      if (e instanceof Unauthorized) { setNeedKey(true); setKeyError("That key was not accepted. Check the start script output."); }
      else setConnected(false);
    }
  }, [loadDetail, select, toast]);

  useEffect(() => {
    if (needKey) return;
    void refresh();
    const t = setInterval(() => void refresh(), 2000);
    return () => clearInterval(t);
  }, [needKey, refresh]);

  const counts = useMemo(() => ({
    action: cases.filter((c) => needsAction(c, now)).length, holds: cases.filter((c) => c.hold_active).length,
    disputes: cases.filter(disputed).length, all: cases.length,
  }), [cases, now]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = cases.filter((c) => view === "action" ? needsAction(c, now) : view === "holds" ? c.hold_active : view === "disputes" ? disputed(c) : true);
    if (tierFilter) list = list.filter((c) => tierFilter.tiers.includes(c.tier));
    if (q) list = list.filter((c) => [c.payee_vpa, c.user_ref, c.case_id].some((s) => s.toLowerCase().includes(q)));
    if (view === "action") list = [...list].sort((a, b) => (Number(b.hold_active) - Number(a.hold_active)) || (RANK[a.tier] - RANK[b.tier]) || (Date.parse(b.created_at) - Date.parse(a.created_at)));
    return list;
  }, [cases, view, tierFilter, query, now]);

  // ↑ / ↓ move through the visible list.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key !== "ArrowDown" && e.key !== "ArrowUp") || (document.activeElement as HTMLElement | null)?.tagName === "INPUT" || !visible.length) return;
      e.preventDefault();
      const i = visible.findIndex((c) => c.case_id === selectedRef.current);
      const next = visible[Math.max(0, Math.min(visible.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))];
      select(next.case_id);
      document.querySelector(`[data-id="${CSS.escape(next.case_id)}"]`)?.scrollIntoView({ block: "nearest" });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, select]);

  const needAnalyst = () => {
    const id = analyst.trim();
    if (!id) { setResult({ id: selectedId, err: true, text: "Enter your analyst ID at the top first." }); document.getElementById("analyst")?.focus(); }
    else { try { localStorage.setItem(ANALYST, id); } catch { /* private mode */ } }
    return id;
  };
  const run = async (path: string, body: object, ok: (r: Record<string, unknown>) => string) => {
    const id = needAnalyst(); if (!id || !detail) return;
    try {
      const r = await api<Record<string, unknown>>(path, { analyst_id: id, ...body });
      const text = ok(r);
      setResult({ id: detail.c.case_id, text }); toast({ kind: "info", title: "Saved", body: text });
    } catch (e) { if (!(e instanceof Unauthorized)) setResult({ id: detail.c.case_id, err: true, text: `Not saved: ${(e as Error).message}` }); }
    await refresh(); if (selectedRef.current) await loadDetail(selectedRef.current);
  };
  const vpaPath = (a: string) => `/v1/payees/${encodeURIComponent(detail!.c.payee_vpa)}/${a}`;
  const actions = {
    release: () => run(`/v1/cases/${encodeURIComponent(selectedId)}/release`, {}, () => "Hold released. The payer's phone unlocks within a few seconds."),
    acceptAppeal: () => run(`/v1/cases/${encodeURIComponent(selectedId)}/accept-appeal`, {}, () => "Appeal accepted."),
    confirm: (note: string) => run(vpaPath("confirm"), { notes: note }, (r) => r.is_confirmed_scam
      ? `Confirmed by ${r.analyst_id}. Every case to ${detail!.c.payee_vpa} is now marked as a scam, and new payments are declined.`
      : `Confirmation recorded for ${r.analyst_id}. A second analyst must also confirm.`),
    clear: (note: string) => run(vpaPath("clear"), { notes: note }, (r) => `Cleared by ${r.analyst_id}. Payments to ${detail!.c.payee_vpa} are no longer declined.`),
    searchFor: (text: string, who: string) => { setView("all"); setTierFilter(null); setQuery(text); toast({ kind: "info", title: who, body: `Showing every check matching ${text}` }); },
    select: (id: string) => select(id),
    copied: (id: string) => toast({ kind: "info", title: "Copied", body: id }),
  };

  const row = detail ? cases.find((c) => c.case_id === detail.c.case_id) ?? detail.c : null;
  const payers = summary?.totals.payers ?? 0;

  return (
    <div className="grid h-screen grid-cols-[404px_1fr] grid-rows-[60px_1fr] overflow-hidden bg-background text-foreground">
      <header className="relative z-30 col-span-2 flex items-center gap-5 border-b bg-card px-[22px] shadow-[0_1px_2px_rgba(16,24,40,.05)]">
        <div className="flex flex-col leading-tight">
          <b className="text-[15.5px] font-semibold tracking-[-.2px]">Satark analyst console</b>
          <span className="text-xs text-muted-foreground">Fraud operations · UPI risk checks</span>
        </div>
        <div className="flex-1" />
        <span className="inline-flex items-center gap-2 rounded-full border bg-[#fbfbfd] px-3 py-1.5 text-[12.5px] whitespace-nowrap text-[#475467]">
          <span className="relative grid size-2 place-items-center">
            {connected && <span className="absolute -inset-1 rounded-full border-2 border-[var(--risk-green)] opacity-0 [animation:ping-soft_2.4s_cubic-bezier(.2,.8,.2,1)_infinite]" />}
            <span className={cn("size-2 rounded-full", connected ? "bg-[var(--risk-green)]" : "bg-[#98a2b3]")} />
          </span>
          {connected ? `Live · ${payers} phone${payers === 1 ? "" : "s"} · ${clock(now)}` : needKey ? "Waiting for the key" : "Not connected"}
        </span>
        <label className="flex items-center gap-2 text-[12.5px] text-muted-foreground">Analyst ID
          <input id="analyst" value={analyst} onChange={(e) => setAnalyst(e.target.value)} placeholder="e.g. analyst_alpha" autoComplete="off"
            className="w-[150px] rounded-lg border bg-card px-2.5 py-1.5 text-foreground outline-none transition focus:border-primary focus:ring-[3px] focus:ring-primary/20" />
        </label>
        <button type="button" onClick={() => { setKeyError(""); setNeedKey(true); }} className="px-1 text-[12.5px] font-medium text-primary">Change key</button>
      </header>

      <Sidebar cases={cases} visible={visible} counts={counts} view={view} setView={setView} query={query} setQuery={setQuery}
        tierFilter={tierFilter} clearTierFilter={() => setTierFilter(null)} selectedId={selectedId} onSelect={(id) => select(id)}
        fresh={fresh} now={now} updated={updated} />

      <main className="min-h-0 overflow-y-auto px-[22px] pt-[18px] pb-6">
        {summary && <Metrics summary={summary} tierFilter={tierFilter} setTierFilter={(f) => { setTierFilter(f); setView("all"); }} />}
        {summary && <Activity cases={cases} summary={summary} points={points} setTierFilter={(f) => { setTierFilter(f); setView("all"); }} />}
        {!selectedId ? (
          <div className="rounded-xl border bg-card px-8 py-16 text-center text-muted-foreground shadow-sm">
            <b className="mb-1.5 block text-base font-semibold text-foreground">Select a case</b>
            Pick a case on the left, or pay from the phone: new red pauses open here on their own.
          </div>
        ) : detail && row ? (
          <CaseView key={detail.c.case_id} detail={detail} row={row} cases={cases} summary={summary} now={now}
            result={result && result.id === detail.c.case_id ? result : null} actions={actions} />
        ) : (
          <div className="space-y-4 rounded-xl border bg-card p-6 shadow-sm">
            <div className="h-4 w-1/3 animate-pulse rounded bg-[#eef0f4]" /><div className="h-7 w-2/3 animate-pulse rounded bg-[#eef0f4]" />
            <div className="h-44 animate-pulse rounded bg-[#eef0f4]" />
          </div>
        )}
      </main>

      {needKey && <KeyDialog error={keyError} onSubmit={(k) => { setKey(k); setKeyError(""); setNeedKey(false); seen.current = null; }} />}
    </div>
  );
}

function KeyDialog({ error, onSubmit }: { error: string; onSubmit: (k: string) => void }) {
  const [k, setK] = useState("");
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(16,24,40,.38)] backdrop-blur-[3px]">
      <form onSubmit={(e) => { e.preventDefault(); if (k.trim()) onSubmit(k.trim()); }}
        className="w-[400px] animate-in fade-in zoom-in-95 rounded-2xl bg-card px-[26px] pt-[26px] pb-[22px] shadow-2xl duration-200">
        <h2 className="mb-1.5 text-lg font-semibold">Analyst key</h2>
        <p className="mb-3.5 text-[13px] text-muted-foreground">The start script prints it as SATARK_ANALYST_KEY. It stays in this browser tab only.</p>
        <input id="key-input" type="password" value={k} onChange={(e) => setK(e.target.value)} autoFocus aria-label="Analyst key" autoComplete="off"
          className="mb-3 w-full rounded-[9px] border px-3 py-[9px] outline-none transition focus:border-primary focus:ring-[3px] focus:ring-primary/20" />
        {error && <p className="mb-3 text-[13px] text-[var(--risk-red-ink)]">{error}</p>}
        <button type="submit" className="w-full rounded-[9px] bg-primary py-2.5 text-[13px] font-medium text-white transition hover:bg-[#2f4fb8]">Open console</button>
      </form>
    </div>
  );
}
