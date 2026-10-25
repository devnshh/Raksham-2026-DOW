import { createContext, useCallback, useContext, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";
import type { CaseRow, Tier } from "@/lib/api";
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

/** What happened to the payment after the check: shown once the phone reports it paid or cancelled. */
export function StatusBadge({ status }: { status: CaseRow["status"] }) {
  if (status === "open") return null;
  return (
    <span className={cn("inline-flex shrink-0 items-center whitespace-nowrap rounded-[5px] border px-[7px] py-[1px] text-[10.5px] font-semibold uppercase tracking-[.5px]",
      status === "completed" ? "border-[#d0d5dd] bg-[#f2f4f7] text-[#344054]" : "border-[#b7e0c5] bg-[var(--risk-green-soft)] text-[var(--risk-green-ink)]")}>
      {status === "completed" ? "Paid" : "Cancelled"}
    </span>
  );
}

/** Hover help. The bubble is plain text: values from the server are never rendered as HTML. It is drawn
 *  on the page body at a fixed position, so overflow-hidden panels never clip it, and kept on screen. */
export function Tip({ text, children, className, side = "top" }: { text: ReactNode; children: ReactNode; className?: string; side?: "top" | "bottom" }) {
  const anchor = useRef<HTMLSpanElement>(null);
  const bubble = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  useLayoutEffect(() => {
    if (!open || !anchor.current || !bubble.current) return;
    const a = anchor.current.getBoundingClientRect(), b = bubble.current.getBoundingClientRect(), gap = 6, edge = 8;
    const above = a.top - gap - b.height, below = a.bottom + gap;
    const top = side === "top" ? (above >= edge ? above : below) : (below + b.height <= innerHeight - edge ? below : above);
    const left = Math.min(Math.max(edge, a.left + a.width / 2 - b.width / 2), innerWidth - edge - b.width);
    setPos({ left, top });
  }, [open, side, text]);
  return (
    <span ref={anchor} className={cn("relative", className)}
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => { setOpen(false); setPos(null); }}>
      {children}
      {open && createPortal(
        <span ref={bubble} role="tooltip" style={{ left: pos?.left ?? -9999, top: pos?.top ?? -9999 }}
          className={cn("pointer-events-none fixed z-[100] w-max max-w-[280px] rounded-md bg-[#101828] px-2.5 py-1.5 text-left text-xs leading-snug font-normal normal-case tracking-normal text-[#f2f4f7] shadow-lg transition-opacity duration-150",
            pos ? "opacity-100" : "opacity-0")}>
          {text}
        </span>, document.body)}
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
