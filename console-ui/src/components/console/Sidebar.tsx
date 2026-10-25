import { Search, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { CaseRow } from "@/lib/api";
import { ago, holdEnd, rupees, whyText } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ScamBadge, Tip, TierBadge } from "./ui";

export type View = "action" | "holds" | "disputes" | "all";
export interface TierFilter { name: string; tiers: string[] }

const EDGE: Record<string, string> = { red: "before:bg-[var(--risk-red)]", amber: "before:bg-[var(--risk-amber)]", green: "before:bg-[var(--risk-green)]", decline: "before:bg-[var(--risk-violet)]" };

export function Sidebar(props: {
  cases: CaseRow[]; visible: CaseRow[]; counts: Record<View, number>; view: View; setView: (v: View) => void;
  query: string; setQuery: (q: string) => void; tierFilter: TierFilter | null; clearTierFilter: () => void;
  selectedId: string; onSelect: (id: string) => void; fresh: Set<string>; now: number; updated: string;
}) {
  const { visible, counts, view, setView, query, setQuery, tierFilter, clearTierFilter, selectedId, onSelect, fresh, now } = props;
  const search = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const inInput = (document.activeElement as HTMLElement | null)?.tagName === "INPUT";
      if (e.key === "/" && !inInput) { e.preventDefault(); search.current?.focus(); }
      if (e.key === "Escape" && document.activeElement === search.current) { setQuery(""); search.current?.blur(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setQuery]);

  const tabs: [View, string][] = [["action", "Needs action"], ["holds", "Holds"], ["disputes", "Disputes"], ["all", "All"]];
  return (
    <aside className="relative z-20 flex min-h-0 flex-col border-r bg-card shadow-[6px_0_24px_-12px_rgba(16,24,40,.18)]" aria-label="Cases">
      <div className="border-b border-[#eef0f4] px-[18px] pt-[18px] pb-3">
        <h1 className="mb-3 flex items-center justify-between text-[17px] font-semibold tracking-[-.25px]">
          Cases <span className="text-xs font-medium text-muted-foreground">{props.updated}</span>
        </h1>
        <div className="grid grid-cols-4 gap-1 rounded-[10px] border border-[#eef0f4] bg-[#f6f7f9] p-1" role="tablist">
          {tabs.map(([v, name]) => (
            <button key={v} type="button" role="tab" aria-selected={view === v} onClick={() => setView(v)}
              className={cn("flex flex-col items-center gap-px rounded-[7px] px-1 pt-[7px] pb-1.5 text-muted-foreground transition-all hover:text-[#475467]",
                view === v && "bg-card text-foreground shadow-sm")}>
              <span className={cn("text-[17px] leading-tight font-semibold text-[#475467] transition-colors", view === v && "text-foreground",
                v === "action" && counts.action > 0 && "text-[var(--risk-red)]")}>{counts[v]}</span>
              <span className="text-[11.5px] font-medium whitespace-nowrap">{name}</span>
            </button>
          ))}
        </div>
        <label className="mt-3 flex items-center gap-2 rounded-[9px] border bg-card px-2.5 py-[7px] transition focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/20">
          <Search className="size-[15px] text-muted-foreground" />
          <input ref={search} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search UPI ID, payer or case"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none" autoComplete="off" />
          <kbd className="rounded border px-1.5 font-mono text-[10.5px] text-muted-foreground shadow-[0_1px_0_#e4e7ec]">/</kbd>
        </label>
        {(tierFilter || query) && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {tierFilter && <FilterChip text={`Showing ${tierFilter.name}`} onClear={clearTierFilter} />}
            {query && <FilterChip text={`Search: ${query}`} onClear={() => setQuery("")} />}
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 pt-2 pb-3.5" role="listbox" aria-label="Cases">
        {visible.length === 0 ? (
          <div className="px-[18px] py-10 text-center text-sm text-muted-foreground">
            {view === "action" && !tierFilter && !query ? "Nothing needs action. New red pauses appear here as they happen." : "No cases match."}
          </div>
        ) : visible.map((c) => {
          const left = c.hold_active ? Math.max(0, Math.min(1, (holdEnd(c) - now) / (c.hold_minutes * 60000))) : 0;
          return (
            <button key={c.case_id} type="button" role="option" aria-selected={c.case_id === selectedId} data-id={c.case_id}
              onClick={() => onSelect(c.case_id)}
              className={cn("relative mb-1 grid w-full grid-cols-[1fr_auto] gap-x-3 gap-y-[3px] rounded-[10px] border border-transparent py-[11px] pr-3 pl-[15px] text-left transition-colors hover:bg-[#f6f7f9]",
                "before:absolute before:top-3 before:bottom-3 before:left-[5px] before:w-[3px] before:rounded before:content-['']", EDGE[c.tier],
                c.case_id === selectedId && "border-[#cfd9fa] bg-[#eef2fd] shadow-sm hover:bg-[#eef2fd]", fresh.has(c.case_id) && "row-fresh")}>
              <span className="min-w-0 truncate font-mono text-[12.5px] font-medium">{c.payee_vpa}</span>
              <span className="text-right text-[13.5px] font-semibold">{rupees(c.amount)}</span>
              <span className="flex min-w-0 items-center gap-[7px] overflow-hidden text-xs whitespace-nowrap text-muted-foreground">
                {c.payee_confirmed_scam ? <ScamBadge /> : <TierBadge tier={c.tier} />}
                <span className="truncate">{whyText(c)}</span>
              </span>
              <span className="text-right text-[11.5px] whitespace-nowrap text-muted-foreground">{ago(c.created_at, now)}</span>
              {c.hold_active && (
                <Tip text="Safety hold · drains as the 30-minute pause runs out" className="col-span-2 mt-1.5 block">
                  <span className="block h-[3px] overflow-hidden rounded bg-[var(--risk-red-line)]">
                    <span className="block h-full origin-left bg-[var(--risk-red)] transition-transform duration-1000 ease-linear" style={{ transform: `scaleX(${left})` }} />
                  </span>
                </Tip>
              )}
            </button>
          );
        })}
      </div>
      <div className="flex justify-between border-t border-[#eef0f4] bg-[#fbfbfd] px-[18px] py-2.5 text-[11.5px] text-muted-foreground">
        <span>{visible.length} of {props.cases.length} checks</span><span>↑ ↓ to move</span>
      </div>
    </aside>
  );
}

function FilterChip({ text, onClear }: { text: string; onClear: () => void }) {
  return (
    <span className="inline-flex animate-in fade-in items-center gap-1.5 rounded-full border border-[#cfd9fa] bg-[#eef2fd] py-[3px] pr-1.5 pl-2.5 text-xs font-medium text-[#2f4fb8]">
      {text}
      <button type="button" onClick={onClear} aria-label="Clear filter" className="grid size-[18px] place-items-center rounded-full hover:bg-primary/15"><X className="size-3" /></button>
    </span>
  );
}
