"""
Database Seeding Script for SATARK Backend.
Populates standard verified merchants, known scam accounts, and baseline user history.
"""

import time
import json
from datetime import datetime, timezone, timedelta

from api.db.connection import get_db, init_db
from api.config import DB_PATH


def seed_data(db_path: str = DB_PATH) -> None:
    """Seeds baseline payees and user historical transactions."""
    init_db(db_path)
    now_dt = datetime.now(timezone.utc)
    now_ms = int(time.time() * 1000)
    now_iso = now_dt.isoformat()
    day_ms = 86_400_000

    with get_db(db_path) as conn:
        # Check if already seeded
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM payees;")
        if cursor.fetchone()["cnt"] > 0:
            return  # already seeded

        # ---------------------------------------------------------------------
        # 1. Payees: Verified Brands & Merchants
        # ---------------------------------------------------------------------
        verified_payees = [
            ("zomato@hdfcbank", "Zomato Media Ltd", True, 1820.0, 4200, 0, "merchant"),
            ("swiggy@axisbank", "Bundl Technologies Pvt Ltd", True, 1600.0, 3800, 0, "merchant"),
            ("chaipoint@icici", "Mountain Trail Foods (Chai Point)", True, 940.0, 240, 0, "merchant"),
            ("amazonpay@ybl", "Amazon Seller Services", True, 2100.0, 8900, 0, "merchant"),
            ("bescom.bill@sbi", "Bangalore Electricity Supply", True, 1500.0, 1200, 0, "utility"),
            ("starbucks@okhdfcbank", "Tata Starbucks Pvt Ltd", True, 1200.0, 310, 0, "merchant"),
        ]

        # ---------------------------------------------------------------------
        # 2. Payees: Regular Individuals & Friends
        # ---------------------------------------------------------------------
        regular_payees = [
            ("rahul.sharma@oksbi", "Rahul Sharma (Friend)", False, 640.0, 1, 0, "friend"),
            ("priya.verma@okaxis", "Priya Verma (Colleague)", False, 430.0, 0, 0, "colleague"),
            ("amit.patel@ibl", "Amit Patel (Flatmate)", False, 720.0, 1, 0, "friend"),
            ("sneha.rao@paytm", "Sneha Rao (Sister)", False, 890.0, 0, 0, "family"),
            ("kirana-store@paytm", "Gupta Daily Provisions", False, 520.0, 8, 0, "retail"),
        ]

        # ---------------------------------------------------------------------
        # 3. Payees: Scam Mule Accounts & Lookalikes
        # ---------------------------------------------------------------------
        scam_payees = [
            ("kyc-helpdesk-update@ybl", "SBI Quick KYC Support Desk", False, 2.5, 19, 4, "mule"),
            ("cbi-verification-dept@ybl", "Cyber Cell Verification Fund", False, 1.0, 8, 2, "mule"),
            ("amaz0n-refund-desk@okaxis", "Amazon Returns Resolution Desk", False, 4.0, 24, 6, "mule"),
            ("task-payout-secure@paytm", "Global VIP Task Payouts", False, 6.0, 32, 5, "mule"),
            ("ipo-allotment-vault@okhdfcbank", "Direct Allotment Depository", False, 3.0, 14, 3, "mule"),
            ("electricity-rebate@oksbi", "Govt Power Rebate Officer", False, 1.5, 12, 3, "mule"),  # demo data: 3 reports keeps this journey red with the ml/train.py model
            ("confirmed-scam-mule@ybl", "National Clearance Vault", False, 0.5, 45, 12, "mule"),
        ]

        all_payees = verified_payees + regular_payees + scam_payees
        for vpa, name, is_verified, age, payers_24h, reports, cat in all_payees:
            # Pre-confirm 'confirmed-scam-mule@ybl' by 2 analysts for testing
            is_confirmed = (vpa == "confirmed-scam-mule@ybl")
            confirmations_json = json.dumps(["analyst_01", "analyst_02"]) if is_confirmed else "[]"
            first_seen_iso = (datetime.now(timezone.utc) - timedelta(days=float(age))).isoformat()

            cursor.execute(
                """
                INSERT OR REPLACE INTO payees (
                    vpa, display_name, first_seen_at, verified, is_merchant,
                    name, is_verified_merchant, account_age_days,
                    new_payers_24h, prior_reports_count, is_confirmed_scam,
                    confirmations, category, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    vpa, name, first_seen_iso, int(bool(is_verified)), int(bool(cat == "merchant")),
                    name, is_verified, age, payers_24h, reports, is_confirmed, confirmations_json, cat, now_iso
                )
            )

            # Fan-in is computed only from real payment rows (no static counter), so seed the
            # recent first-time payers as payments spread over the last ~23 hours. Verified
            # merchants are skipped: fan-in only matters for unverified payees. Re-seed before a
            # demo (scripts/reset_demo_db.py) because these age out after 24 hours.
            if not is_verified and payers_24h >= 2:
                for p_idx in range(1, payers_24h + 1):
                    hours_ago = 1.0 + (p_idx * 22.0 / payers_24h)
                    cursor.execute(
                        "INSERT INTO payments (payer_id, payee_vpa, amount, created_at) VALUES (?, ?, ?, ?);",
                        (f"seed_payer_{vpa.split('@')[0]}_{p_idx:02d}", vpa, 2000.0 + p_idx * 500.0,
                         (now_dt - timedelta(hours=hours_ago)).isoformat())
                    )

            # Also populate scam_registry if reports > 0
            if reports > 0:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO scam_registry (vpa, report_count, confirmed_at, source)
                    VALUES (?, ?, ?, 'seed');
                    """,
                    (vpa, reports, now_iso)
                )

        # ---------------------------------------------------------------------
        # 4. Seed User Baselines for 'raksham@oksbi' and 'default_user'
        # ---------------------------------------------------------------------
        test_users = ["raksham@oksbi", "default_user", "u-hash-9f2c"]
        for u in test_users:
            # Accounts opened about 13 months ago, so their scam reports carry full weight.
            cursor.execute("INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?);",
                           (u, (now_dt - timedelta(days=400)).isoformat()))

        # 12 regular payments over past 30 days (typical UPI pattern)
        regular_payments = [
            ("chaipoint@icici", 45.0, 10),
            ("zomato@hdfcbank", 280.0, 13),
            ("swiggy@axisbank", 340.0, 20),
            ("rahul.sharma@oksbi", 500.0, 18),
            ("priya.verma@okaxis", 200.0, 15),
            ("kirana-store@paytm", 150.0, 11),
            ("bescom.bill@sbi", 1250.0, 16),
            ("chaipoint@icici", 60.0, 17),
            ("zomato@hdfcbank", 420.0, 21),
            ("amit.patel@ibl", 650.0, 19),
            ("groceries@okaxis", 380.0, 12),
            ("petrol-bunk@oksbi", 500.0, 9),
        ]

        for u in test_users:
            for idx, (payee, amt, hour) in enumerate(regular_payments):
                # Spread timestamps over past 30 days
                ts = now_ms - ((30 - idx * 2) * day_ms)
                created_str = (now_dt - timedelta(days=float(30 - idx * 2))).isoformat()
                typing_ms = 280.0 + (idx % 3) * 15.0
                pauses = idx % 2
                pin_secs = 3.2 + (idx % 4) * 0.3

                cursor.execute(
                    """
                    INSERT INTO transactions (
                        user_id, payee_vpa, amount, hour, timestamp_ms,
                        typing_ms, pauses, pin_secs, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (u, payee, amt, hour, ts, typing_ms, pauses, pin_secs, created_str)
                )

                cursor.execute(
                    """
                    INSERT INTO payments (
                        payer_id, payee_vpa, amount, created_at
                    ) VALUES (?, ?, ?, ?);
                    """,
                    (u, payee, amt, created_str)
                )

                cursor.execute(
                    """
                    INSERT INTO sessions (
                        user_id, typing_ms, pauses, pin_secs, timestamp_ms
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (u, typing_ms, pauses, pin_secs, ts)
                )


if __name__ == "__main__":
    seed_data()
    print("Database seeded successfully.")

