"""
SQLite Implementation of Feature Store for SATARK Backend.
Maintains user baselines, session dynamics, and payee registry.
"""

import time
import math
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List

from api.db.connection import get_db
from api.store.interface import BaseFeatureStore
from api.lookalike.detector import compute_lookalike_score
from api.config import DB_PATH

# Account age is only known for payees whose data came from the seed/registry. Rows we created
# ourselves on first sight, on a user report, or on an analyst flag carry no real age.
UNKNOWN_AGE_CATEGORIES = {"unknown", "reported", "flagged"}
# Neutral value fed to the model when age is unknown (typical established individual account).
NEUTRAL_UNKNOWN_AGE_DAYS = 365.0


def _median(data: List[float]) -> float:
    """Computes median of numeric list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    mid = n // 2
    if n % 2 == 1:
        return sorted_data[mid]
    return (sorted_data[mid - 1] + sorted_data[mid]) / 2.0


class SQLiteFeatureStore(BaseFeatureStore):
    """SQLite feature store implementation."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def compute_baseline_features(
        self,
        user_id: str,
        payee_vpa: str,
        amount: float,
        current_hour: Optional[int] = None
    ) -> Dict[str, Any]:
        clean_user = user_id.strip().lower()
        clean_payee = payee_vpa.strip().lower()
        now_ms = int(time.time() * 1000)
        day_ms = 86_400_000

        if current_hour is None:
            current_hour = datetime.now().hour

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT amount, hour, timestamp_ms, payee_vpa
                FROM transactions
                WHERE user_id = ?
                ORDER BY timestamp_ms ASC;
                """,
                (clean_user,)
            )
            rows = cursor.fetchall()

        past_amounts = [float(r["amount"]) for r in rows]
        ready = len(past_amounts) >= 5

        if ready:
            median_amt = _median(past_amounts)
            amount_ratio = round(amount / median_amt, 2) if median_amt > 0 else 1.0

            log_amounts = [math.log(max(a, 1.0)) for a in past_amounts]
            log_median = _median(log_amounts)
            log_deviations = [abs(a - log_median) for a in log_amounts]
            mad = _median(log_deviations)
            scale = max(1.4826 * mad, 0.25)
            current_log = math.log(max(amount, 1.0))
            amount_z = round((current_log - log_median) / scale, 2)

            max_amt = max(past_amounts)
            amount_vs_max = round(amount / max(max_amt, 1.0), 2)

            # Circular hour familiarity [h-1, h, h+1]
            familiar_hours = {(current_hour - 1) % 24, current_hour, (current_hour + 1) % 24}
            familiar_count = sum(1 for r in rows if r["hour"] in familiar_hours)
            hour_familiarity = round(familiar_count / len(past_amounts), 2)
        else:
            default_cohort_median = 450.0
            amount_ratio = round(amount / default_cohort_median, 2)
            amount_z = 0.0
            amount_vs_max = 1.0
            hour_familiarity = 0.125

        # Same payee stats in last 24h
        last_24h_txns = [
            r for r in rows
            if r["payee_vpa"].lower() == clean_payee and r["timestamp_ms"] >= (now_ms - day_ms)
        ]
        same_payee_count_24h = len(last_24h_txns)
        same_payee_sum_24h = round(sum(float(r["amount"]) for r in last_24h_txns), 2)

        # Escalation ratio: current amount vs last transaction to same payee
        payee_past_txns = [r for r in rows if r["payee_vpa"].lower() == clean_payee]
        if payee_past_txns:
            last_txn = max(payee_past_txns, key=lambda x: x["timestamp_ms"])
            last_amt = float(last_txn["amount"])
            escalation_ratio = round(amount / last_amt, 2) if last_amt > 0 else 1.0
            payee_first_time = False
        else:
            escalation_ratio = 1.0
            payee_first_time = True

        return {
            "amount": amount,
            "amount_ratio": amount_ratio,
            "amount_z": amount_z,
            "amount_vs_max": amount_vs_max,
            "hour": current_hour,
            "hour_familiarity": hour_familiarity,
            "same_payee_count_24h": same_payee_count_24h,
            "same_payee_sum_24h": same_payee_sum_24h,
            "escalation_ratio": escalation_ratio,
            "baseline_ready": ready,
            "payee_first_time": payee_first_time
        }

    def compute_timing_z_scores(
        self,
        user_id: str,
        typing_ms: Optional[float],
        pauses: Optional[int],
        pin_secs: Optional[float]
    ) -> Dict[str, float]:
        """Robust z-scores vs the user's own last 50 sessions. A value the phone could not
        measure (None) scores 0, i.e. "no evidence", never an invented default. PIN time is
        unknown at risk-check time (the check runs before the PIN screen)."""
        clean_user = user_id.strip().lower()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT typing_ms, pauses, pin_secs
                FROM sessions
                WHERE user_id = ?
                ORDER BY timestamp_ms DESC
                LIMIT 50;
                """,
                (clean_user,)
            )
            rows = cursor.fetchall()

        if len(rows) < 5:
            return {"typing_z": 0.0, "pause_z": 0.0, "pin_time_z": 0.0}

        typing_list = [float(r["typing_ms"]) for r in rows]
        t_med = _median(typing_list)
        t_mad = _median([abs(x - t_med) for x in typing_list])
        t_scale = max(1.4826 * t_mad, 0.05 * t_med)
        typing_z = round((typing_ms - t_med) / t_scale, 2) if typing_ms is not None else 0.0

        pause_list = [float(r["pauses"]) for r in rows]
        p_med = _median(pause_list)
        p_mad = _median([abs(x - p_med) for x in pause_list])
        p_scale = max(1.4826 * p_mad, 0.5)
        pause_z = round((float(pauses) - p_med) / p_scale, 2) if pauses is not None else 0.0

        pin_list = [float(r["pin_secs"]) for r in rows]
        pin_med = _median(pin_list)
        pin_mad = _median([abs(x - pin_med) for x in pin_list])
        pin_scale = max(1.4826 * pin_mad, 0.1 * pin_med)
        pin_time_z = round((pin_secs - pin_med) / pin_scale, 2) if pin_secs is not None else 0.0

        return {
            "typing_z": typing_z,
            "pause_z": pause_z,
            "pin_time_z": pin_time_z
        }

    def get_payee_profile(self, payee_vpa: str, exclude_payer: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves (or registers) a payee profile.
        - payee_age_days: real account age only when known (seeded / registry data). A payee we
          simply have not seen before has UNKNOWN age: the model gets a neutral value and no
          "young account" reason is ever shown. Days-since-first-seen is NOT account age.
        - payee_new_payers_24h: distinct payers whose first-ever payment to this payee was in the
          last 24h, from completed payments only, excluding the current payer.
        - payee_reports_prior: analyst/registry report count + distinct in-app reporters.
        """
        clean_vpa = payee_vpa.strip().lower()
        clean_payer = (exclude_payer or "").strip().lower()
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        cutoff_24h_iso = (now_dt - timedelta(hours=24)).isoformat()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT vpa, display_name, first_seen_at, verified, is_merchant,
                       name, is_verified_merchant, account_age_days,
                       is_confirmed_scam, confirmations, category
                FROM payees
                WHERE vpa = ?;
                """,
                (clean_vpa,)
            )
            row = cursor.fetchone()

            if row:
                payee_age_known = (
                    row["account_age_days"] is not None
                    and (row["category"] or "") not in UNKNOWN_AGE_CATEGORIES
                )
                payee_age_days = NEUTRAL_UNKNOWN_AGE_DAYS
                if payee_age_known:
                    payee_age_days = float(row["account_age_days"])
                    if row["first_seen_at"]:
                        try:
                            first_dt = datetime.fromisoformat(row["first_seen_at"].replace("Z", "+00:00"))
                            payee_age_days = max(0.0, (now_dt - first_dt).total_seconds() / 86400.0)
                        except Exception:
                            pass

                verified_val = row["verified"] if row["verified"] is not None else row["is_verified_merchant"]
                payee_verified = bool(verified_val)
                is_merchant = bool(row["is_merchant"] or row["is_verified_merchant"])
                display_name = row["display_name"] or row["name"] or clean_vpa
                is_confirmed_scam = bool(row["is_confirmed_scam"])
                try:
                    confirmations = json.loads(row["confirmations"] or "[]")
                except Exception:
                    confirmations = []
                category = row["category"] or ("merchant" if is_merchant else "regular")
            else:
                # Never seen before: register it, but its account age is unknown (NULL).
                payee_age_known = False
                payee_age_days = NEUTRAL_UNKNOWN_AGE_DAYS
                payee_verified = False
                is_merchant = False
                display_name = "First-Seen Payee"
                is_confirmed_scam = False
                confirmations = []
                category = "unknown"
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO payees (
                        vpa, display_name, first_seen_at, verified, is_merchant,
                        name, is_verified_merchant, account_age_days, new_payers_24h,
                        prior_reports_count, is_confirmed_scam, confirmations, category, updated_at
                    ) VALUES (?, ?, ?, 0, 0, ?, 0, NULL, 0, 0, 0, '[]', 'unknown', ?);
                    """,
                    (clean_vpa, display_name, now_iso, display_name, now_iso)
                )

            # Fan-in: distinct OTHER payers whose first completed payment to this payee was in the last 24h.
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt FROM (
                    SELECT payer_id, MIN(created_at) AS first_payment
                    FROM payments
                    WHERE payee_vpa = ? AND payer_id != ?
                    GROUP BY payer_id
                    HAVING first_payment >= ?
                );
                """,
                (clean_vpa, clean_payer, cutoff_24h_iso)
            )
            payers_row = cursor.fetchone()
            payee_new_payers_24h = int(payers_row["cnt"]) if payers_row and payers_row["cnt"] is not None else 0

            payee_reports_prior = self._report_total(cursor, clean_vpa)
            lookalike = compute_lookalike_score(clean_vpa, is_verified=payee_verified)

            return {
                "payee_vpa": clean_vpa,
                "payee_name": display_name,
                "payee_verified": payee_verified,
                "is_merchant": is_merchant,
                "payee_age_days": round(payee_age_days, 1),
                "payee_age_known": payee_age_known,
                "payee_new_payers_24h": int(payee_new_payers_24h),
                "payee_reports_prior": int(payee_reports_prior),
                "lookalike_score": lookalike,
                "is_confirmed_scam": is_confirmed_scam,
                "confirmations": confirmations,
                "category": category,
                "signal_status": "known"
            }

    @staticmethod
    def _report_total(cursor, clean_vpa: str) -> int:
        """Analyst/registry report count plus distinct in-app reporters (one per reporter)."""
        cursor.execute("SELECT report_count FROM scam_registry WHERE vpa = ?;", (clean_vpa,))
        reg = cursor.fetchone()
        registry_count = int(reg["report_count"]) if reg and reg["report_count"] is not None else 0
        cursor.execute("SELECT COUNT(DISTINCT reporter_id) AS cnt FROM reports WHERE payee_vpa = ?;", (clean_vpa,))
        users = cursor.fetchone()
        return registry_count + (int(users["cnt"]) if users and users["cnt"] is not None else 0)

    def get_trusted_payee_history(self, user_id: str, payee_vpa: str) -> Tuple[int, int]:
        clean_user = user_id.strip().lower()
        clean_payee = payee_vpa.strip().lower()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp_ms
                FROM transactions
                WHERE user_id = ? AND payee_vpa = ?
                ORDER BY timestamp_ms ASC;
                """,
                (clean_user, clean_payee)
            )
            rows = cursor.fetchall()

        if not rows:
            return 0, 0

        count = len(rows)
        first_ts = rows[0]["timestamp_ms"]
        last_ts = rows[-1]["timestamp_ms"]
        history_days = int((last_ts - first_ts) / 86_400_000)

        return count, history_days

    def get_user_amber_count_in_window(self, user_id: str, days: int = 7) -> int:
        clean_user = user_id.strip().lower()
        cutoff_ms = int(time.time() * 1000) - (days * 86_400_000)
        cutoff_iso = datetime.fromtimestamp(cutoff_ms / 1000.0, tz=timezone.utc).isoformat()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as cnt
                FROM cases
                WHERE user_id = ? AND tier = 'amber' AND created_at >= ?;
                """,
                (clean_user, cutoff_iso)
            )
            row = cursor.fetchone()
            return int(row["cnt"]) if row else 0

    def record_case(
        self,
        case_id: str,
        txn_ref: Optional[str],
        user_id: str,
        payee_vpa: str,
        amount: float,
        tier: str,
        reasons: List[str],
        template_id: str,
        hold_minutes: int,
        feature_vector: Dict[str, Any],
        evidence_pack: Dict[str, Any]
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cases (
                    case_id, txn_ref, user_id, payee_vpa, amount, tier,
                    reasons, template_id, hold_minutes, feature_vector,
                    evidence_pack, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    case_id,
                    txn_ref,
                    user_id.strip().lower(),
                    payee_vpa.strip().lower(),
                    amount,
                    tier,
                    json.dumps(reasons),
                    template_id,
                    hold_minutes,
                    json.dumps(feature_vector),
                    json.dumps(evidence_pack),
                    now_iso
                )
            )

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cases WHERE case_id = ?;", (case_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def list_cases(
        self,
        tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            if tier:
                cursor.execute(
                    """
                    SELECT case_id, user_id, payee_vpa, amount, tier, reasons,
                           template_id, hold_minutes, created_at, evidence_pack
                    FROM cases
                    WHERE tier = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?;
                    """,
                    (tier.lower(), limit, offset)
                )
            else:
                cursor.execute(
                    """
                    SELECT case_id, user_id, payee_vpa, amount, tier, reasons,
                           template_id, hold_minutes, created_at, evidence_pack
                    FROM cases
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?;
                    """,
                    (limit, offset)
                )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def record_report(
        self,
        report_id: str,
        reporter_id: str,
        payee_vpa: str,
        reason: str,
        notes: Optional[str]
    ) -> int:
        """
        Records an in-app scam report. Each reporter counts once per payee, so repeated taps or a
        single abusive user cannot inflate the count. Returns the payee's total report count.
        """
        clean_payee = payee_vpa.strip().lower()
        clean_reporter = reporter_id.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM reports WHERE reporter_id = ? AND payee_vpa = ? LIMIT 1;",
                (clean_reporter, clean_payee)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO reports (report_id, reporter_id, payee_vpa, reason, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (report_id, clean_reporter, clean_payee, reason, notes or "", now_iso)
                )
            # Register an unknown payee without inventing age, fan-in or report numbers.
            cursor.execute(
                """
                INSERT OR IGNORE INTO payees (
                    vpa, display_name, first_seen_at, name, is_verified_merchant, account_age_days,
                    new_payers_24h, prior_reports_count, is_confirmed_scam, confirmations, category, updated_at
                ) VALUES (?, 'Reported Payee', ?, 'Reported Payee', 0, NULL, 0, 0, 0, '[]', 'reported', ?);
                """,
                (clean_payee, now_iso, now_iso)
            )
            return self._report_total(cursor, clean_payee)

    def confirm_scam_payee(
        self,
        payee_vpa: str,
        analyst_id: str,
        notes: Optional[str]
    ) -> Tuple[int, bool]:
        clean_payee = payee_vpa.strip().lower()
        clean_analyst = analyst_id.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()

            # Record confirmation event
            cursor.execute(
                """
                INSERT INTO analyst_confirmations (payee_vpa, analyst_id, notes, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (clean_payee, clean_analyst, notes or "", now_iso)
            )

            # Check existing payee record
            cursor.execute(
                "SELECT confirmations, is_confirmed_scam FROM payees WHERE vpa = ?;",
                (clean_payee,)
            )
            row = cursor.fetchone()

            if row:
                try:
                    confirmations = set(json.loads(row["confirmations"] or "[]"))
                except Exception:
                    confirmations = set()
            else:
                confirmations = set()

            confirmations.add(clean_analyst)
            confirmations_list = sorted(list(confirmations))
            is_confirmed = len(confirmations_list) >= 2

            if row:
                cursor.execute(
                    """
                    UPDATE payees
                    SET confirmations = ?, is_confirmed_scam = ?, updated_at = ?
                    WHERE vpa = ?;
                    """,
                    (json.dumps(confirmations_list), is_confirmed, now_iso, clean_payee)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO payees (
                        vpa, display_name, first_seen_at, name, is_verified_merchant, account_age_days,
                        new_payers_24h, prior_reports_count, is_confirmed_scam,
                        confirmations, category, updated_at
                    ) VALUES (?, 'Analyst Flagged Payee', ?, 'Analyst Flagged Payee', 0, NULL, 0, 0, ?, ?, 'flagged', ?);
                    """,
                    (clean_payee, now_iso, is_confirmed, json.dumps(confirmations_list), now_iso)
                )

            return len(confirmations_list), is_confirmed

    def trust_pair(self, user_id: str, payee_vpa: str, source: str, case_id: str) -> None:
        """Records that this user's payments to this payee were vouched for. An analyst's word
        replaces a user's; a user's never replaces an analyst's."""
        with get_db(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO trusted_pairs (user_id, payee_vpa, source, case_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, payee_vpa) DO UPDATE SET source = excluded.source,
                    case_id = excluded.case_id, created_at = excluded.created_at
                WHERE trusted_pairs.source != 'analyst';
                """,
                (user_id.strip().lower(), payee_vpa.strip().lower(), source, case_id,
                 datetime.now(timezone.utc).isoformat())
            )

    def get_pair_trust(self, user_id: str, payee_vpa: str) -> Optional[str]:
        """'analyst', 'user' or None."""
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT source FROM trusted_pairs WHERE user_id = ? AND payee_vpa = ?;",
                (user_id.strip().lower(), payee_vpa.strip().lower())
            ).fetchone()
        return row["source"] if row else None

    def clear_payee(self, payee_vpa: str) -> List[str]:
        """Analyst clear: withdraws every confirmation so payments are no longer declined. User reports
        stay on record. Returns the confirmations that were withdrawn."""
        clean_payee = payee_vpa.strip().lower()
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT confirmations FROM payees WHERE vpa = ?;", (clean_payee,))
            row = cursor.fetchone()
            if not row:
                return []
            cursor.execute(
                "UPDATE payees SET confirmations = '[]', is_confirmed_scam = 0, updated_at = ? WHERE vpa = ?;",
                (datetime.now(timezone.utc).isoformat(), clean_payee)
            )
            try:
                return json.loads(row["confirmations"] or "[]")
            except Exception:
                return []

    def payee_overview(self, payee_vpa: str, case_limit: int = 20) -> Dict[str, Any]:
        """Read-only analyst view of a payee: the 24 h fan-in cluster (each distinct payer whose first
        completed payment was in the last 24 h), reports, confirmations and recent cases."""
        clean_payee = payee_vpa.strip().lower()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT display_name, confirmations, is_confirmed_scam FROM payees WHERE vpa = ?;",
                           (clean_payee,))
            row = cursor.fetchone()
            cursor.execute(
                """
                SELECT payer_id, MIN(created_at) AS first_payment, COUNT(*) AS payments, SUM(amount) AS total
                FROM payments WHERE payee_vpa = ?
                GROUP BY payer_id HAVING first_payment >= ?
                ORDER BY first_payment;
                """,
                (clean_payee, cutoff)
            )
            payers = [dict(r) for r in cursor.fetchall()]
            reports = self._report_total(cursor, clean_payee)
            cursor.execute(
                """
                SELECT case_id, user_id, amount, tier, reasons, created_at FROM cases
                WHERE payee_vpa = ? ORDER BY created_at DESC LIMIT ?;
                """,
                (clean_payee, case_limit)
            )
            cases = [dict(r) for r in cursor.fetchall()]
        try:
            confirmations = json.loads(row["confirmations"] or "[]") if row else []
        except Exception:
            confirmations = []
        return {
            "payee_vpa": clean_payee,
            "known": row is not None,
            "display_name": row["display_name"] if row else None,
            "is_confirmed_scam": bool(row["is_confirmed_scam"]) if row else False,
            "confirmations": confirmations,
            "reports": reports,
            "new_payers_24h": payers,
            "recent_cases": [{**c, "reasons": json.loads(c["reasons"] or "[]")} for c in cases],
        }

    def record_payment(
        self,
        payer_id: str,
        payee_vpa: str,
        amount: float,
        created_at: Optional[str] = None
    ) -> int:
        """Records a COMPLETED payment (called after the PIN succeeds, never at risk-check time)."""
        clean_payer = payer_id.strip().lower()
        clean_payee = payee_vpa.strip().lower()
        now_dt = datetime.now(timezone.utc)
        created_str = created_at or now_dt.isoformat()
        now_ms = int(time.time() * 1000)

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO payments (payer_id, payee_vpa, amount, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (clean_payer, clean_payee, float(amount), created_str)
            )
            payment_id = cursor.lastrowid

            # Also maintain transactions table for user baseline features
            cursor.execute(
                """
                INSERT INTO transactions (user_id, payee_vpa, amount, hour, timestamp_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (clean_payer, clean_payee, float(amount), now_dt.hour, now_ms, created_str)
            )

        return payment_id or 1

    def upsert_scam_registry(
        self,
        vpa: str,
        source: str = "analyst",
        report_count: Optional[int] = None
    ) -> int:
        """
        Scam registry write path: confirms/increments report_count for a VPA.
        Returns the updated report_count.
        """
        clean_vpa = vpa.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_count FROM scam_registry WHERE vpa = ?;", (clean_vpa,))
            row = cursor.fetchone()

            if row:
                new_count = report_count if report_count is not None else int(row["report_count"]) + 1
                cursor.execute(
                    """
                    UPDATE scam_registry
                    SET report_count = ?, confirmed_at = ?, source = ?
                    WHERE vpa = ?;
                    """,
                    (new_count, now_iso, source, clean_vpa)
                )
            else:
                new_count = report_count if report_count is not None else 1
                cursor.execute(
                    """
                    INSERT INTO scam_registry (vpa, report_count, confirmed_at, source)
                    VALUES (?, ?, ?, ?);
                    """,
                    (clean_vpa, new_count, now_iso, source)
                )

            # Keep payees.prior_reports_count in sync if payee exists
            cursor.execute(
                "UPDATE payees SET prior_reports_count = ?, updated_at = ? WHERE vpa = ?;",
                (new_count, now_iso, clean_vpa)
            )

        return new_count

    def record_session(self, user_id: str, typing_ms: Optional[float], pauses: Optional[int],
                       pin_secs: Optional[float]) -> None:
        """Adds a completed payment's typing rhythm to the user's timing baseline (only measured values)."""
        if typing_ms is None or pin_secs is None:
            return
        with get_db(self.db_path) as conn:
            conn.cursor().execute(
                "INSERT INTO sessions (user_id, typing_ms, pauses, pin_secs, timestamp_ms) VALUES (?, ?, ?, ?, ?);",
                (user_id.strip().lower(), float(typing_ms), int(pauses or 0), float(pin_secs), int(time.time() * 1000))
            )

    def update_case_decision(self, case_id: str, tier: str, reasons: List[str], template_id: str,
                             hold_minutes: int, evidence_updates: Dict[str, Any]) -> None:
        """Updates a case's decision (questionnaire can only raise it) and merges evidence."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT evidence_pack FROM cases WHERE case_id = ?;", (case_id,))
            row = cursor.fetchone()
            evidence = json.loads(row["evidence_pack"] or "{}") if row else {}
            evidence.update(evidence_updates)
            cursor.execute(
                """
                UPDATE cases SET tier = ?, reasons = ?, template_id = ?, hold_minutes = ?, evidence_pack = ?
                WHERE case_id = ?;
                """,
                (tier, json.dumps(reasons), template_id, hold_minutes, json.dumps(evidence), case_id)
            )
