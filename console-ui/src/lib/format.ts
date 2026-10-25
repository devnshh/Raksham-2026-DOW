import type { CaseRow, Tier } from "./api";

export const TIER: Record<Tier, string> = { red: "Red pause", amber: "Amber", green: "Passed", decline: "Declined" };
export const TIER_COLOR: Record<Tier, string> = {
  red: "var(--risk-red)", amber: "var(--risk-amber)", green: "var(--risk-green)", decline: "var(--risk-violet)",
};

export const LABELS: Record<string, string> = {
  ON_CALL: "On a call", SCREEN_SHARED: "Screen shared", REMOTE_APP_NEW: "New remote-access app",
  REMOTE_APP_PRESENT: "Remote-access app", REMOTE_APP_ACTIVE: "Remote-access app", FAN_IN_24H: "Many new payers",
  PAYEE_REPORTED: "Reported by others", AMOUNT_UNUSUAL: "Unusual amount", NEW_PAYEE: "First payment to them",
  NEW_PAYEE_YOUNG_ACCOUNT: "Young account", UNVERIFIED_PAYEE: "Unverified payee", LOOKALIKE_HANDLE: "Look-alike handle",
  UNUSUAL_HOUR: "Unusual hour", QR_ENTRY: "QR code", LINK_ENTRY: "Opened from a link", BAD_LINK: "Known bad link",
  SESSION_PRESSURE: "Hesitant typing", NOTE_INTENT_RISK: "Scam-like note", ESCALATING_PAYMENTS: "Escalating payments",
  REPEAT_PAYEE_24H: "Repeat payee today", ANALYST_CONFIRMED_SCAM: "Analyst-confirmed scam", CHECK_UNAVAILABLE: "Check unavailable",
  USER_REPORTED_GUIDANCE: "User says someone is guiding them", COLLECT_REQUEST: "Collect request",
};
export const EXPLAIN: Record<string, string> = {
  ON_CALL: "The payer was on a phone call while paying.", SCREEN_SHARED: "The phone's screen was being shared or cast.",
  REMOTE_APP_NEW: "A remote-access app was installed in the last 24 hours.", REMOTE_APP_PRESENT: "A remote-access app is installed.",
  FAN_IN_24H: "Five or more people paid this account for the first time in 24 hours: the mule pattern.",
  PAYEE_REPORTED: "Other users reported this account as a scam.", AMOUNT_UNUSUAL: "At least twice the payer's usual amount.",
  NEW_PAYEE: "The payer has not paid this account before.", NEW_PAYEE_YOUNG_ACCOUNT: "The receiving account is under 30 days old.",
  UNVERIFIED_PAYEE: "Not a verified merchant.", LOOKALIKE_HANDLE: "The UPI ID imitates a brand or bank.",
  UNUSUAL_HOUR: "The payer rarely pays at this hour.", BAD_LINK: "The payment came from a link our intel marks as bad.",
  SESSION_PRESSURE: "Typing and pauses differ from how this payer usually types.", NOTE_INTENT_RISK: "The note matches a common scam story.",
  ESCALATING_PAYMENTS: "Each payment to this account is bigger than the last.", ANALYST_CONFIRMED_SCAM: "Two analysts confirmed this account as a scam.",
  COLLECT_REQUEST: "A request to take money from the payer.", USER_REPORTED_GUIDANCE: "The payer said someone is telling them what to do.",
};
export const HOT = new Set(["PAYEE_REPORTED", "FAN_IN_24H", "SCREEN_SHARED", "REMOTE_APP_NEW", "BAD_LINK", "ANALYST_CONFIRMED_SCAM",
  "USER_REPORTED_GUIDANCE", "LOOKALIKE_HANDLE", "COLLECT_REQUEST", "NOTE_INTENT_RISK"]);
export const label = (c: string) => LABELS[c] || c.toLowerCase().replace(/_/g, " ").replace(/^./, (m) => m.toUpperCase());

export const CHANNEL: Record<string, string> = {
  contact: "Contact", qr_scan: "QR scan", qr_gallery: "QR from gallery", typed_vpa: "Typed UPI ID",
  deep_link_sms: "SMS link", deep_link_whatsapp: "WhatsApp link", merchant_collect: "Collect request",
};
export const FAMILY: Record<string, [string, string]> = {
  A: ["Session", "Call, screen share, remote-access app, typing pressure"],
  B: ["Payee", "Reports, new payers, account age, look-alike name"],
  C: ["Context", "Bad link, scam-like note, how the payee was entered"],
  D: ["Behaviour", "Amount against usual, hour, escalation"],
};

export const rupees = (n: number) => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
export const compactRupees = (n: number) =>
  n >= 1e7 ? `₹${(n / 1e7).toFixed(1)}Cr` : n >= 1e5 ? `₹${(n / 1e5).toFixed(n >= 1e6 ? 0 : 1)}L` : rupees(n);
export const clock = (d: string | number | Date) =>
  new Date(d).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
export const hm = (d: string | number | Date) => new Date(d).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
export const ago = (iso: string, now = Date.now()) => {
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  return s < 45 ? "now" : s < 3600 ? `${Math.round(s / 60)} min` : s < 86400 ? `${Math.round(s / 3600)} h` : `${Math.round(s / 86400)} d`;
};
export const mmss = (ms: number) => { const s = Math.max(0, Math.ceil(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
export const holdEnd = (c: CaseRow) => new Date(c.created_at).getTime() + c.hold_minutes * 60000;

export const disputed = (c: CaseRow) => c.dispute === "false_alarm_pending";
export const needsAction = (c: CaseRow, now = Date.now()) => c.hold_active || disputed(c) || (c.tier === "red" && c.status === "open")
  || (c.tier === "decline" && now - new Date(c.created_at).getTime() < 3600e3);
export const whyText = (c: CaseRow) => c.payee_confirmed_scam && c.tier !== "decline" ? "Payee since confirmed as a scam"
  : c.tier === "green" ? "No warning" : disputed(c) ? "User reported a false alarm"
  : c.reasons.slice(0, 2).map(label).join(" · ") || TIER[c.tier];
