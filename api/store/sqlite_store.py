"""
SQLite Implementation of Feature Store for SATARK Backend.
Maintains user baselines, session dynamics, and payee registry.
"""

import time
import math
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from zoneinfo import ZoneInfo

from api.db.connection import get_db
from api.store.interface import BaseFeatureStore
from api.lookalike.detector import compute_lookalike_score
from api.config import DB_PATH

# Account age is only known for payees whose data came from the seed/registry. Rows we created
# ourselves on first sight, on a user report, or on an analyst flag carry no real age.
UNKNOWN_AGE_CATEGORIES = {"unknown", "reported", "flagged"}
# Neutral value fed to the model when age is unknown (typical established individual account).
NEUTRAL_UNKNOWN_AGE_DAYS = 365.0
# Reporter trust: full weight at 30 days and 5 completed payments; newer accounts together add at most this.
NEW_REPORTERS_CAP = 0.5


# Payment hours are Indian local time everywhere (the model and the seeds use them), whatever the server's
# timezone. Storing the UTC hour while scoring the server's local hour made a user's usual hour look unusual.
IST = ZoneInfo("Asia/Kolkata")


def local_hour(ts: Optional[datetime] = None) -> int:
    return (ts or datetime.now(timezone.utc)).astimezone(IST).hour


def reporter_weight(age_days: float, payments: int) -> float:
    return min(1.0, max(0.0, age_days) / 30.0) * min(1.0, payments / 5.0)


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
            current_hour = local_hour()

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
        """
        Analyst/registry report count plus in-app reports weighted by each reporter's history.
        A reporter counts fully once their account is 30 days old and has 5 completed payments,
        and proportionally before that. Account age comes from the users table when there is a row
        (seeded accounts), else from the reporter's first completed payment; unknown accounts count
        as brand new (weight 0). A report counts only from someone who dealt with this payee (a risk
        check or a payment to them), so nobody can flag a business they never paid. All
        not-yet-established reporters together add at most half a report, so a crowd of fresh
        accounts can never flag a payee on its own. Each reporter counts once per payee.
        """
        cursor.execute("SELECT report_count FROM scam_registry WHERE vpa = ?;", (clean_vpa,))
        reg = cursor.fetchone()
        registry_count = int(reg["report_count"]) if reg and reg["report_count"] is not None else 0
        cursor.execute(
            """
            SELECT r.reporter_id,
                   COALESCE(
                       julianday('now') - julianday((SELECT MIN(u.created_at) FROM users u
                                                     WHERE u.user_id = r.reporter_id)),
                       julianday('now') - julianday((SELECT MIN(t.timestamp_ms) FROM transactions t
                                                     WHERE t.user_id = r.reporter_id) / 1000.0, 'unixepoch'),
                       0) AS age_days,
                   (SELECT COUNT(*) FROM transactions t WHERE t.user_id = r.reporter_id) AS payments,
                   EXISTS (SELECT 1 FROM cases c WHERE c.user_id = r.reporter_id AND c.payee_vpa = ?)
                       OR EXISTS (SELECT 1 FROM transactions t
                                  WHERE t.user_id = r.reporter_id AND t.payee_vpa = ?) AS dealt
            FROM (SELECT DISTINCT reporter_id FROM reports WHERE payee_vpa = ?) r;
            """,
            (clean_vpa, clean_vpa, clean_vpa)
        )
        established, newcomers = 0.0, 0.0
        for row in cursor.fetchall():
            if not row["dealt"]:
                continue
            w = reporter_weight(row["age_days"], row["payments"])
            if w >= 1.0:
                established += 1.0
            else:
                newcomers += w
        return registry_count + int(established + min(NEW_REPORTERS_CAP, newcomers))

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

    def red_cases_for_pair(self, user_id: str, payee_vpa: str, within_hours: int = 24) -> List[Dict[str, Any]]:
        """This user's red cases for this payee in the last `within_hours`, newest first."""
        since = (datetime.now(timezone.utc) - timedelta(hours=within_hours)).isoformat()
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM cases
                WHERE user_id = ? AND payee_vpa = ? AND tier = 'red' AND created_at >= ?
                ORDER BY created_at DESC;
                """,
                (user_id.strip().lower(), payee_vpa.strip().lower(), since)
            )
            return [dict(r) for r in cursor.fetchall()]

    def cases_since(self, hours: int) -> List[Dict[str, Any]]:
        """Every case of the last `hours` hours (analyst console summary), oldest first."""
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with get_db(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT case_id, user_id, amount, tier, hold_minutes, evidence_pack, created_at FROM cases
                WHERE created_at >= ? ORDER BY created_at;
                """,
                (since,)
            ).fetchall()
        return [dict(r) for r in rows]

    def confirmed_scam_payees(self, vpas: List[str]) -> set:
        """Which of these payees two analysts have confirmed as scams."""
        if not vpas:
            return set()
        marks = ",".join("?" for _ in vpas)
        with get_db(self.db_path) as conn:
            rows = conn.execute(f"SELECT vpa FROM payees WHERE is_confirmed_scam = 1 AND vpa IN ({marks});", list(vpas)).fetchall()
        return {r["vpa"] for r in rows}

    def recent_amounts(self, user_id: str, limit: int = 60) -> List[Tuple[float, int]]:
        """The user's last completed payments as (amount, timestamp_ms), newest first (analyst console)."""
        with get_db(self.db_path) as conn:
            rows = conn.execute(
                "SELECT amount, timestamp_ms FROM transactions WHERE user_id = ? ORDER BY timestamp_ms DESC LIMIT ?;",
                (user_id.strip().lower(), limit)
            ).fetchall()
        return [(float(r["amount"]), int(r["timestamp_ms"])) for r in rows]

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

    def trust_pair(self, user_id: str, payee_vpa: str, source: str, case_id: str, reports_at_trust: int) -> None:
        """Records that this user's payments to this payee were vouched for. An analyst's word
        replaces a user's; a user's never replaces an analyst's."""
        with get_db(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO trusted_pairs (user_id, payee_vpa, source, case_id, reports_at_trust, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, payee_vpa) DO UPDATE SET source = excluded.source, case_id = excluded.case_id,
                    reports_at_trust = excluded.reports_at_trust, created_at = excluded.created_at
                WHERE trusted_pairs.source != 'analyst' OR excluded.source = 'analyst';
                """,
                (user_id.strip().lower(), payee_vpa.strip().lower(), source, case_id, int(reports_at_trust),
                 datetime.now(timezone.utc).isoformat())
            )

    def get_pair_trust(self, user_id: str, payee_vpa: str, current_reports: int,
                       max_age_days: int = 90) -> Tuple[Optional[str], Optional[float]]:
        """('analyst' or 'user', the amount of the vouched case), or (None, None). Trust lapses with
        age, and as soon as the payee has been reported more often than when the trust was given."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        with get_db(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT tp.source, c.amount FROM trusted_pairs tp LEFT JOIN cases c ON c.case_id = tp.case_id
                WHERE tp.user_id = ? AND tp.payee_vpa = ? AND tp.created_at >= ? AND tp.reports_at_trust >= ?;
                """,
                (user_id.strip().lower(), payee_vpa.strip().lower(), cutoff, int(current_reports))
            ).fetchone()
        return (row["source"], row["amount"]) if row else (None, None)

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
            cursor.execute("SELECT created_at FROM payments WHERE payee_vpa = ? AND created_at >= ? ORDER BY created_at;",
                           (clean_payee, cutoff))
            payments_24h = [r["created_at"] for r in cursor.fetchall()]
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
            "payments_24h": payments_24h,  # every completed payment in 24 h, repeat payers included
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
                (clean_payer, clean_payee, float(amount), local_hour(now_dt), now_ms, created_str)
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
        """Updates a case's decision (questionnaire can only raise it) and merges evidence. The merge
        happens inside one UPDATE, so two concurrent updates (a payment completing while a report or
        questionnaire lands) cannot overwrite each other's keys. Keys are internal names, never user input."""
        sets = ", ".join(f"'$.\"{k}\"', json(?)" for k in evidence_updates)
        evidence_sql = f"json_set(COALESCE(evidence_pack, '{{}}'), {sets})" if evidence_updates else "evidence_pack"
        with get_db(self.db_path) as conn:
            conn.execute(
                f"""
                UPDATE cases SET tier = ?, reasons = ?, template_id = ?, hold_minutes = ?, evidence_pack = {evidence_sql}
                WHERE case_id = ?;
                """,
                (tier, json.dumps(reasons), template_id, hold_minutes,
                 *[json.dumps(v) for v in evidence_updates.values()], case_id)
            )

    def claim_completion(self, case_id: str) -> bool:
        """Marks an open case as paid in one statement: True only for the call that did it, False if it was
        already paid or cancelled. A double tap or a retry must not record two payments."""
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE cases SET evidence_pack = json_set(evidence_pack, '$.completed', json('true'), '$.completed_at', ?)
                WHERE case_id = ? AND json_extract(evidence_pack, '$.completed') IS NULL
                  AND json_extract(evidence_pack, '$.cancelled') IS NULL;
                """,
                (datetime.now(timezone.utc).isoformat(), case_id)
            )
            return cur.rowcount == 1
