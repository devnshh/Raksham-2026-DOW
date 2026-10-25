// Analyst API client. The key lives in this browser tab only (sessionStorage).

export type Tier = "green" | "amber" | "red" | "decline";

export interface CaseRow {
  case_id: string;
  user_ref: string;
  payee_vpa: string;
  amount: number;
  tier: Tier;
  reasons: string[];
  template_id: string;
  hold_minutes: number;
  created_at: string;
  status: "open" | "completed" | "cancelled";
  dispute: string | null;
  hold_active: boolean;
  payee_confirmed_scam: boolean;
  evidence_pack?: Evidence | null;
}

export interface Evidence {
  features?: Record<string, number | boolean | string | null>;
  score?: number | null;
  family_contrib?: Record<string, number>;
  applied_rules?: string[];
  audit?: { sequence?: number };
  payee_age_known?: boolean;
  dispute?: string;
  appeal_accepted_by?: string;
  hold_released_by?: string;
  hold_released_at?: string;
  completed?: boolean;
  completed_at?: string;
  cancelled?: boolean;
  cancelled_by_user?: boolean;
}

export interface Summary {
  generated_at: string;
  hours: number;
  totals: {
    checks: number; green: number; amber: number; red: number; decline: number; warnings: number;
    holds_running: number; disputes_pending: number; money_held: number; payers: number;
  };
  hourly: { hour_start: string; checks: number; warnings: number; red: number }[];
  cutoffs: { amber: number; red: number } | null;
  family_thresholds: Record<string, number>;
  hold_minutes: number;
}

export interface PayeeView {
  payee_vpa: string;
  known: boolean;
  is_confirmed_scam: boolean;
  confirmations: string[];
  reports: number;
  new_payers_24h: { payer_id: string; first_payment: string; payments: number; total: number }[];
  payments_24h: string[];
}

export interface PayerAmounts {
  user_id: string;
  amounts: number[];
  median: number | null;
  payments: { amount: number; at: string }[];
}

export class Unauthorized extends Error {}

const KEY = "satark.key";
export const getKey = () => { try { return sessionStorage.getItem(KEY) || ""; } catch { return ""; } };
export const setKey = (k: string) => { try { sessionStorage.setItem(KEY, k); } catch { /* private mode */ } };

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-API-Key": getKey(), ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401) throw new Unauthorized("That key was not accepted.");
  if (!res.ok) {
    let text = `The server answered ${res.status}.`;
    try { const j = await res.json(); if (typeof j.detail === "string") text = j.detail; } catch { /* not JSON */ }
    throw new Error(text);
  }
  return res.json() as Promise<T>;
}
