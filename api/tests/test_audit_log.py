"""
Unit tests for Hash-chained, Append-only Audit Log.
"""

from api.store.audit_store import AuditLogStore, GENESIS_HASH
from api.db.connection import get_db


def test_audit_hash_chaining(audit_store: AuditLogStore):
    """Verifies that every row stores the SHA256 hash of the preceding row."""
    entry1 = audit_store.append_log(
        case_id="case_001",
        user_id="user1@oksbi",
        payee_vpa="payee1@ybl",
        tier="green",
        reasons=[]
    )
    assert entry1["sequence"] >= 1
    assert entry1["curr_hash"] is not None

    entry2 = audit_store.append_log(
        case_id="case_002",
        user_id="user1@oksbi",
        payee_vpa="payee2@ybl",
        tier="red",
        reasons=["ON_CALL", "LOOKALIKE_HANDLE"]
    )
    assert entry2["sequence"] == entry1["sequence"] + 1
    assert entry2["prev_hash"] == entry1["curr_hash"]

    # Verify overall integrity
    is_valid, count, msg = audit_store.verify_chain()
    assert is_valid is True
    assert count >= 2


def test_tamper_detection(audit_store: AuditLogStore):
    """Modifying any field in an existing row breaks chain verification."""
    # Append entry
    entry = audit_store.append_log(
        case_id="case_tamper",
        user_id="victim@oksbi",
        payee_vpa="scam@ybl",
        tier="red",
        reasons=["ON_CALL"]
    )

    # Directly tamper with SQLite data behind the store's back
    with get_db(audit_store.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE audit_log SET tier = 'green' WHERE case_id = 'case_tamper';"
        )

    # Chain verification must catch the tampering
    is_valid, bad_idx, err_msg = audit_store.verify_chain()
    assert is_valid is False
    assert "tampering detected" in err_msg.lower() or "broken" in err_msg.lower()

