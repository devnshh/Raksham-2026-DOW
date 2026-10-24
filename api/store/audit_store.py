"""
Cryptographic, Append-only, Hash-chained Audit Log for SATARK.
Ensures non-repudiation and tamper detection for all risk assessments.
"""

import json
import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from api.db.connection import get_db
from api.config import DB_PATH, POLICY_VERSION, MODEL_VERSION

GENESIS_HASH = "0" * 64
_audit_lock = threading.Lock()


class AuditLogStore:
    """Manages the append-only hash-chained audit trail."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    @staticmethod
    def compute_row_hash(
        sequence: int,
        prev_hash: str,
        timestamp: str,
        case_id: str,
        user_id: str,
        payee_vpa: str,
        tier: str,
        reasons: List[str],
        model_version: str,
        policy_version: str
    ) -> str:
        """Deterministically hashes an audit row."""
        reasons_canonical = json.dumps(sorted(reasons))
        payload = (
            f"{sequence}|{prev_hash}|{timestamp}|{case_id}|"
            f"{user_id.lower()}|{payee_vpa.lower()}|{tier.lower()}|"
            f"{reasons_canonical}|{model_version}|{policy_version}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append_log(
        self,
        case_id: str,
        user_id: str,
        payee_vpa: str,
        tier: str,
        reasons: List[str],
        model_version: str = MODEL_VERSION,
        policy_version: str = POLICY_VERSION,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Appends a hash-chained audit row. Thread-safe and atomic.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        with _audit_lock:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # Get latest sequence and hash
                cursor.execute(
                    "SELECT sequence, curr_hash FROM audit_log ORDER BY sequence DESC LIMIT 1;"
                )
                last_row = cursor.fetchone()

                if last_row:
                    sequence = int(last_row["sequence"]) + 1
                    prev_hash = last_row["curr_hash"]
                else:
                    sequence = 1
                    prev_hash = GENESIS_HASH

                curr_hash = self.compute_row_hash(
                    sequence=sequence,
                    prev_hash=prev_hash,
                    timestamp=timestamp,
                    case_id=case_id,
                    user_id=user_id,
                    payee_vpa=payee_vpa,
                    tier=tier,
                    reasons=reasons,
                    model_version=model_version,
                    policy_version=policy_version
                )

                reasons_json = json.dumps(reasons)
                cursor.execute(
                    """
                    INSERT INTO audit_log (
                        sequence, prev_hash, curr_hash, timestamp,
                        case_id, user_id, payee_vpa, tier,
                        reasons, model_version, policy_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        sequence,
                        prev_hash,
                        curr_hash,
                        timestamp,
                        case_id,
                        user_id.strip().lower(),
                        payee_vpa.strip().lower(),
                        tier.strip().lower(),
                        reasons_json,
                        model_version,
                        policy_version
                    )
                )

                return {
                    "sequence": sequence,
                    "prev_hash": prev_hash,
                    "curr_hash": curr_hash,
                    "timestamp": timestamp,
                    "case_id": case_id
                }

    def verify_chain(self) -> Tuple[bool, int, str]:
        """
        Verifies the cryptographic integrity of the entire audit chain.
        Returns: (is_valid, verified_rows_count, message)
        """
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_log ORDER BY sequence ASC;")
            rows = cursor.fetchall()

        if not rows:
            return True, 0, "Audit log is empty (genesis state)."

        expected_prev_hash = GENESIS_HASH
        expected_seq = 1

        for idx, row in enumerate(rows):
            seq = int(row["sequence"])
            prev_hash = row["prev_hash"]
            curr_hash = row["curr_hash"]
            timestamp = row["timestamp"]
            case_id = row["case_id"]
            user_id = row["user_id"]
            payee_vpa = row["payee_vpa"]
            tier = row["tier"]
            model_ver = row["model_version"]
            policy_ver = row["policy_version"]

            try:
                reasons = json.loads(row["reasons"] or "[]")
            except Exception:
                reasons = []

            # 1. Verify sequence continuity
            if seq != expected_seq:
                return False, idx, f"Sequence gap: expected {expected_seq}, found {seq} at row {idx+1}"

            # 2. Verify backward pointer matches previous block hash
            if prev_hash != expected_prev_hash:
                return False, idx, f"Hash chain broken at row {seq}: prev_hash does not match preceding curr_hash"

            # 3. Recompute hash and verify content tampering
            recomputed = self.compute_row_hash(
                sequence=seq,
                prev_hash=prev_hash,
                timestamp=timestamp,
                case_id=case_id,
                user_id=user_id,
                payee_vpa=payee_vpa,
                tier=tier,
                reasons=reasons,
                model_version=model_ver,
                policy_version=policy_ver
            )

            if recomputed != curr_hash:
                return False, idx, f"Data tampering detected at row {seq}: computed hash {recomputed} != stored {curr_hash}"

            expected_prev_hash = curr_hash
            expected_seq += 1

        return True, len(rows), f"Audit log verified: {len(rows)} chained entries intact."

