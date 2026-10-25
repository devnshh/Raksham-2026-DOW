import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { Tier } from "@/lib/api";
import { TIER } from "@/lib/format";

const BADGE: Record<Tier, string> = {
  red: "bg-[var(--risk-red-soft)] text-[var(--risk-red-ink)]",
  amber: "bg-[var(--risk-amber-soft)] text-[var(--risk-amber-ink)]",
  green: "bg-[var(--risk-green-soft)] text-[var(--risk-green-ink)]",
  decline: "bg-[var(--risk-violet-soft)] text-[var(--risk-violet)]",
};

export function TierBadge({ tier, label }: { tier: Tier; label?: string }) {
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-[5px] px-[7px] py-[2px] text-[10.5px] font-semibold uppercase tracking-[.5px]", BADGE[tier])}>
      <span className="size-1.5 rounded-full bg-current" />{label ?? TIER[tier]}
    </span>
  );
}

export function ScamBadge() {
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-[5px] bg-[var(--risk-violet)] px-[7px] py-[2px] text-[10.5px] font-semibold uppercase tracking-[.5px] text-white">
      Scam payee
    </span>
  );
}

/** Hover help. The bubble is plain text: values from the server are never rendered as HTML. */
export function Tip({ text, children, className, side = "top" }: { text: ReactNode; children: ReactNode; className?: string; side?: "top" | "bottom" }) {
  return (
    <span className={cn("group/tip relative", className)}>
      {children}
      <span role="tooltip"
        className={cn("pointer-events-none absolute left-1/2 z-50 w-max max-w-[280px] -translate-x-1/2 rounded-md bg-[#101828] px-2.5 py-1.5 text-left text-xs leading-snug font-normal normal-case tracking-normal text-[#f2f4f7] opacity-0 shadow-lg transition duration-150 group-hover/tip:opacity-100",
          side === "top" ? "bottom-[calc(100%+6px)] translate-y-1 group-hover/tip:translate-y-0" : "top-[calc(100%+6px)] -translate-y-1 group-hover/tip:translate-y-0")}>
        {text}
      </span>
    </span>
  );
}

export function Panel({ title, aside, children, className }: { title: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("flex min-w-0 flex-col px-5 pt-4 pb-5", className)}>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-[13.5px] font-semibold">{title}</h3>
        {aside ? <div className="truncate text-xs text-muted-foreground">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Caps({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("text-[11px] font-semibold uppercase tracking-[.6px] text-muted-foreground", className)}>{children}</div>;
}

export function Stat({ k, v, flag, tip }: { k: string; v: ReactNode; flag?: boolean; tip: string }) {
  return (
    <Tip text={tip} className="block min-w-0">
      <div className={cn("min-w-0 rounded-[9px] border px-2.5 py-[7px] transition-shadow hover:shadow-sm",
        flag ? "border-[var(--risk-red-line)] bg-[var(--risk-red-soft)]" : "border-[#eef0f4] bg-[#fbfbfd]")}>
        <div className="truncate text-[11.5px] text-muted-foreground">{k}</div>
        <div className={cn("mt-px truncate text-[15px] font-semibold", flag && "text-[var(--risk-red-ink)]")}>{v}</div>
      </div>
    </Tip>
  );
}

/* ---------- Toasts ---------- */
interface Toast { id: number; title: string; body: ReactNode; kind: "alert" | "info" | "decline"; onClick?: () => void }
const ToastCtx = createContext<(t: Omit<Toast, "id">) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function Toaster({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((x) => [...x, { ...t, id }]);
    setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), t.kind === "info" ? 2600 : 6500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed right-5 bottom-5 z-50 flex flex-col gap-2.5" aria-live="assertive">
        {toasts.map((t) => (
          <button key={t.id} type="button" onClick={() => { t.onClick?.(); setToasts((x) => x.filter((y) => y.id !== t.id)); }}
            className="grid w-[340px] animate-in grid-cols-[10px_1fr] items-baseline gap-x-2.5 rounded-xl border bg-card px-3.5 py-3 text-left shadow-xl duration-300 fade-in slide-in-from-right-6">
            <span className={cn("size-2 translate-y-[-1px] rounded-full", t.kind === "alert" ? "bg-[var(--risk-red)]" : t.kind === "decline" ? "bg-[var(--risk-violet)]" : "bg-primary")} />
            <b className={cn("block text-[13px]", t.kind === "info" ? "text-primary" : "text-[var(--risk-red-ink)]")}>{t.title}</b>
            <span className="col-start-2 text-[12.5px] text-[#475467]">{t.body}</span>
          </button>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
