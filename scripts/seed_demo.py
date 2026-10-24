"""
Idempotent Demo Seeding Script for SATARK (RAKSHAM Hackathon Track 02).
Populates:
1. Demo user (raksham@oksbi / demo_user) with 90 days of payment history and typing baseline.
2. Legit payees seen in the app: Rahul Sharma, Priya, Amit, Sneha, Vikram (100+ days old), Chai Point, Swiggy.
3. 4 mule payees: 1-5 days old, unverified, 8-20 distinct recent payers in payments table, report_count 0-3 in scam_registry.
4. Small domains JSON with 3 bad domains (young age) and 3 normal domains.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure project root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.config import DB_PATH
from api.db.connection import get_db, init_db


def seed_demo_data(db_path: str = DB_PATH) -> None:
    """Seeds canonical demo data idempotently."""
    init_db(db_path)
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    now_ms = int(now_dt.timestamp() * 1000)
    day_ms = 86_400_000

    print(f"[SEED] Initializing and seeding demo database at: {db_path}")

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # ---------------------------------------------------------------------
        # 1. Seed Legit Payees (Seen in app, 100+ days ago)
        # ---------------------------------------------------------------------
        legit_payees = [
            # vpa, display_name, days_ago, verified, is_merchant, category
            ("rahul.sharma@oksbi", "Rahul Sharma", 120, 0, 0, "friend"),
            ("priya.verma@okaxis", "Priya Verma", 110, 1, 0, "colleague"),
            ("amit.patel@ibl", "Amit Patel", 105, 0, 0, "friend"),
            ("sneha.rao@paytm", "Sneha Rao", 115, 1, 0, "family"),
            ("vikram.singh@oksbi", "Vikram Singh", 100, 0, 0, "friend"),
            ("chaipoint@icici", "Chai Point", 200, 1, 1, "merchant"),
            ("swiggy@axisbank", "Swiggy", 300, 1, 1, "merchant"),
            ("zomato@hdfcbank", "Zomato", 350, 1, 1, "merchant")
        ]

        for vpa, display_name, days_ago, verified, is_merchant, category in legit_payees:
            first_seen_iso = (now_dt - timedelta(days=days_ago)).isoformat()
            cursor.execute(
                """
                INSERT OR REPLACE INTO payees (
                    vpa, display_name, first_seen_at, verified, is_merchant,
                    name, is_verified_merchant, account_age_days, new_payers_24h,
                    prior_reports_count, is_confirmed_scam, confirmations, category, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, '[]', ?, ?);
                """,
                (
                    vpa, display_name, first_seen_iso, verified, is_merchant,
                    display_name, verified, float(days_ago), category, now_iso
                )
            )

        # ---------------------------------------------------------------------
        # 2. Seed 4 Mule Payees (1 to 5 days ago, unverified, recent fan-in)
        # ---------------------------------------------------------------------
        mule_configs = [
            # vpa, display_name, days_ago, recent_payers_count, report_count
            ("kyc-helpdesk-update@ybl", "SBI Quick KYC Support Desk", 2.5, 19, 4),
            ("mule.fastcash@okaxis", "FastCash Payout Mule", 2, 18, 3),
            ("mule.kycsupport@ybl", "Quick KYC Support Mule", 1, 14, 2),
            ("mule.taskpayout@paytm", "VIP Task Payout Mule", 3, 10, 1),
            ("mule.unreported@ibl", "Fresh Unreported Mule", 4, 8, 0),  # Not-yet-reported mule
        ]

        for vpa, display_name, days_ago, payers_count, reports_count in mule_configs:
            first_seen_iso = (now_dt - timedelta(days=days_ago)).isoformat()

            # Insert into payees table
            cursor.execute(
                """
                INSERT OR REPLACE INTO payees (
                    vpa, display_name, first_seen_at, verified, is_merchant,
                    name, is_verified_merchant, account_age_days, new_payers_24h,
                    prior_reports_count, is_confirmed_scam, confirmations, category, updated_at
                ) VALUES (?, ?, ?, 0, 0, ?, 0, ?, ?, ?, 0, '[]', 'mule', ?);
                """,
                (
                    vpa, display_name, first_seen_iso, display_name,
                    float(days_ago), payers_count, reports_count, now_iso
                )
            )

            # Insert into scam_registry
            cursor.execute(
                """
                INSERT OR REPLACE INTO scam_registry (vpa, report_count, confirmed_at, source)
                VALUES (?, ?, ?, ?);
                """,
                (vpa, reports_count, now_iso if reports_count > 0 else None, "analyst_console")
            )

            # Clean any old mock payments for this mule before re-seeding
            cursor.execute("DELETE FROM payments WHERE payee_vpa = ?;", (vpa,))

            # Seed distinct payers whose FIRST EVER payment was in the last 24h
            for p_idx in range(1, payers_count + 1):
                payer_id = f"victim_payer_{vpa.split('@')[0]}_{p_idx:02d}"
                # Spread payment creation time between 1 and 23 hours ago
                hours_ago = 1.0 + (p_idx * 21.0 / max(payers_count, 1))
                payment_time_iso = (now_dt - timedelta(hours=hours_ago)).isoformat()
                amount = 2500.0 + (p_idx * 750.0)

                cursor.execute(
                    """
                    INSERT INTO payments (payer_id, payee_vpa, amount, created_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (payer_id, vpa, amount, payment_time_iso)
                )

        # ---------------------------------------------------------------------
        # 3. Seed Demo Users with 90 Days of Baseline History
        # ---------------------------------------------------------------------
        demo_users = ["raksham@oksbi", "default_user", "demo_user"]
        for u in demo_users:
            cursor.execute("INSERT OR REPLACE INTO users (user_id, created_at) VALUES (?, ?);", (u, now_iso))

            # Clean old baseline txns & sessions for idempotency
            cursor.execute("DELETE FROM transactions WHERE user_id = ?;", (u,))
            cursor.execute("DELETE FROM sessions WHERE user_id = ?;", (u,))

            # 90 days of transactions (spread across rahul, priya, swiggy, chai point)
            base_txns = [
                ("rahul.sharma@oksbi", 450.0, 14, 280.0, 0, 3.2),
                ("swiggy@axisbank", 320.0, 13, 275.0, 0, 3.0),
                ("chaipoint@icici", 180.0, 10, 260.0, 0, 2.9),
                ("priya.verma@okaxis", 600.0, 16, 285.0, 0, 3.3),
                ("amit.patel@ibl", 500.0, 19, 270.0, 0, 3.1),
            ]

            for d_idx in range(88, 0, -2):  # Every 2 days for 90 days
                target_payee, amt, hour, typing_ms, pauses, pin_s = base_txns[d_idx % len(base_txns)]
                ts_ms = now_ms - (d_idx * day_ms)
                created_dt = now_dt - timedelta(days=d_idx)
                created_str = created_dt.isoformat()

                cursor.execute(
                    """
                    INSERT INTO transactions (
                        user_id, payee_vpa, amount, hour, timestamp_ms,
                        typing_ms, pauses, pin_secs, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (u, target_payee, amt, hour, ts_ms, typing_ms, pauses, pin_s, created_str)
                )

                # Also record in payments table
                cursor.execute(
                    """
                    INSERT INTO payments (payer_id, payee_vpa, amount, created_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (u, target_payee, amt, created_str)
                )

            # 50 normal typing sessions
            for s_idx in range(50):
                s_ms = now_ms - ((50 - s_idx) * 3600_000 * 4)  # every 4 hours
                cursor.execute(
                    """
                    INSERT INTO sessions (user_id, typing_ms, pauses, pin_secs, timestamp_ms)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (u, 270.0 + (s_idx % 15), 0, 3.1 + (s_idx % 3) * 0.1, s_ms)
                )

        conn.commit()

    # -------------------------------------------------------------------------
    # 4. Ensure domains.json is written with 3 bad and 3 normal domains
    # -------------------------------------------------------------------------
    domains_dir = _ROOT / "api" / "intel"
    domains_dir.mkdir(parents=True, exist_ok=True)
    domains_file = domains_dir / "domains.json"

    domains_data = {
        "kyc-verification-desk.top": {
            "bad": 1,
            "age_days": 4,
            "category": "phishing",
            "threat_type": "credential_theft"
        },
        "sbi-refund-portal.xyz": {
            "bad": 1,
            "age_days": 7,
            "category": "impersonation",
            "threat_type": "bank_impersonation"
        },
        "cbi-cybercell-fund.online": {
            "bad": 1,
            "age_days": 12,
            "category": "scam",
            "threat_type": "extortion"
        },
        "hdfcbank.com": {
            "bad": 0,
            "age_days": 7300,
            "category": "banking",
            "threat_type": "legitimate"
        },
        "swiggy.com": {
            "bad": 0,
            "age_days": 3650,
            "category": "food",
            "threat_type": "legitimate"
        },
        "zomato.com": {
            "bad": 0,
            "age_days": 4000,
            "category": "food",
            "threat_type": "legitimate"
        }
    }
    domains_file.write_text(json.dumps(domains_data, indent=2), encoding="utf-8")
    print(f"[SEED] Successfully seeded demo payees, mules, history, and {domains_file}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo database for SATARK.")
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite database")
    args = parser.parse_args()
    seed_demo_data(args.db)
