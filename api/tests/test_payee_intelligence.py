"""
Tests for Simulated Payee Intelligence Layer (RAKSHAM Hackathon Track 02).
Covers:
(a) Known verified old contact + small amount -> green
(b) Mule payee + large amount + on_call + screen_shared -> red
(c) Same payee after POST /internal/scam-registry has a higher fusion score
(d) First-seen VPA is registered unverified with UNKNOWN age (neutral value, never "young")
(e) Link entry with bad domain sets link_bad=1, failed lookup gives None
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from api.main import app as risk_api_app
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.policy.engine import PolicyEngine
from api.policy.scorer import get_satark_scorer
from api.intel.domain_intel import lookup_domain
from api.routers.assess import get_feature_store, get_audit_store, get_policy_engine
from scripts.seed_demo import seed_demo_data


@pytest.fixture
def demo_test_client(test_db_path: str):
    """Initializes and seeds full demo database, overriding dependencies."""
    seed_demo_data(test_db_path)
    store = SQLiteFeatureStore(test_db_path)
    audit = AuditLogStore(test_db_path)
    policy = PolicyEngine(scorer=get_satark_scorer())

    risk_api_app.dependency_overrides[get_feature_store] = lambda: store
    risk_api_app.dependency_overrides[get_audit_store] = lambda: audit
    risk_api_app.dependency_overrides[get_policy_engine] = lambda: policy

    with TestClient(risk_api_app) as client:
        yield client, store, policy


# -----------------------------------------------------------------------------
# Test (a): Known verified old contact + small amount -> green
# -----------------------------------------------------------------------------
def test_a_known_verified_old_contact_small_amount_green(demo_test_client):
    """
    Test (a): Payment to a known verified old contact (priya.verma@okaxis, first_seen > 100 days)
    with small amount (₹250) and normal session dynamics produces GREEN tier.
    """
    client, store, _ = demo_test_client
    payload = {
        "txn_ref": "t-legit-01",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "priya.verma@okaxis",
        "amount": 250.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": False,
            "screen_shared": False,
            "remote_app_present": False,
            "remote_app_new": False,
            "typing_ms": 275.0,
            "pauses": 0,
            "pin_secs": 3.1
        },
        "context": {
            "note_intent": "food",
            "note_text": "lunch split"
        }
    }

    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["tier"] == "green"
    assert data["hold_minutes"] == 0
    assert data["reasons"] == [], "Green tier must never include reasons"
    assert "case_id" in data


# -----------------------------------------------------------------------------
# Test (b): Mule payee + large amount + on_call + screen_shared -> red
# -----------------------------------------------------------------------------
def test_b_mule_payee_large_amount_coerced_red(demo_test_client):
    """
    Test (b): Coerced payment (on_call=True, screen_shared=True) with large amount (₹48,000)
    to a mule payee (mule.fastcash@okaxis, unverified, young, 18 recent payers, 3 prior reports)
    produces RED tier with 30-minute hold.
    """
    client, store, _ = demo_test_client
    payload = {
        "txn_ref": "t-mule-01",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "mule.fastcash@okaxis",
        "amount": 48000.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": True,
            "screen_shared": True,
            "remote_app_present": False,
            "remote_app_new": False,
            "app_switches": 3,
            "typing_ms": 480.0,
            "pauses": 3,
            "pin_secs": 8.5
        },
        "context": {
            "note_intent": "kyc",
            "note_text": "cbi fee"
        }
    }

    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["tier"] == "red"
    assert data["hold_minutes"] == 30
    assert len(data["reasons"]) > 0
    assert "ON_CALL" in data["reasons"] or "SCREEN_SHARED" in data["reasons"]


# -----------------------------------------------------------------------------
# Test (c): Same payee after POST /internal/scam-registry has higher score
# -----------------------------------------------------------------------------
def test_c_scam_registry_write_path_elevates_fusion_score(demo_test_client):
    """
    Test (c): POST /internal/scam-registry increments report_count for a VPA.
    Comparing the fusion score before and after confirms the second assessment has a higher score.
    """
    client, store, _ = demo_test_client
    target_vpa = "mule.unreported@ibl"
    headers = {"X-API-Key": "satark-internal-secret-2026"}

    # 1. Profile before analyst confirmation
    prof_before = store.get_payee_profile(target_vpa)
    initial_reports = prof_before["payee_reports_prior"]
    assert initial_reports == 0, "Unreported mule should initially have report_count 0"

    # Construct test features
    base_features = {
        "on_call": False,
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "app_switches": 0,
        "typing_z": 0.0,
        "pause_z": 0.0,
        "pin_time_z": 0.0,
        "device_new": False,
        "failed_auth": 0,
        "payee_first_time": True,
        "payee_age_days": float(prof_before["payee_age_days"]),
        "payee_verified": prof_before["payee_verified"],
        "payee_new_payers_24h": int(prof_before["payee_new_payers_24h"]),
        "payee_reports_prior": initial_reports,
        "lookalike_score": float(prof_before["lookalike_score"]),
        "amount": 25000.0,
        "amount_ratio": 5.0,
        "amount_z": 2.1,
        "amount_vs_max": 1.2,
        "hour": 15,
        "hour_familiarity": 0.5,
        "same_payee_count_24h": 0,
        "same_payee_sum_24h": 0.0,
        "escalation_ratio": 1.0,
        "baseline_ready": True,
        "entry_channel": "typed_vpa"
    }

    scorer = get_satark_scorer()
    score_before = scorer.score(base_features, note_intent="none")["fusion_score"]

    # 2. Analyst confirms mule via POST /internal/scam-registry
    confirm_resp = client.post(
        "/internal/scam-registry",
        json={"vpa": target_vpa, "source": "analyst_console", "notes": "Confirmed mule wallet"},
        headers=headers
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["status"] == "confirmed"
    assert confirm_data["vpa"] == target_vpa
    assert confirm_data["report_count"] == initial_reports + 1

    # 3. Profile after analyst confirmation
    prof_after = store.get_payee_profile(target_vpa)
    assert prof_after["payee_reports_prior"] == initial_reports + 1

    # 4. Re-score with updated payee_reports_prior
    updated_features = dict(base_features)
    updated_features["payee_reports_prior"] = prof_after["payee_reports_prior"]

    score_after = scorer.score(updated_features, note_intent="none")["fusion_score"]

    print(f"\n[FUSION SCORE COMPARISON]: Before={score_before:.5f} -> After={score_after:.5f}")
    assert score_after > score_before, (
        f"Expected score_after ({score_after:.5f}) > score_before ({score_before:.5f})"
    )


# -----------------------------------------------------------------------------
# Test (d): A first-seen VPA is created with age 0 and unverified
# -----------------------------------------------------------------------------
def test_d_first_seen_vpa_created_with_age_zero_and_unverified(demo_test_client):
    """
    Test (d): A VPA never seen before is registered unverified, but its account age is
    UNKNOWN: days-since-first-seen is not account age. The model gets the neutral value
    and no "young account" reason can be shown. (Changed: it used to be age 0.0.)
    """
    client, store, _ = demo_test_client
    unique_vpa = f"brand-new-payee-{uuid.uuid4().hex[:6]}@okaxis"

    # Profile lookup automatically triggers creation
    profile = store.get_payee_profile(unique_vpa)

    assert profile["payee_vpa"] == unique_vpa
    assert profile["payee_age_known"] is False, "First sight says nothing about account age"
    assert profile["payee_age_days"] == 365.0, "Unknown age uses the neutral value"
    assert profile["payee_verified"] is False, "New VPA must be unverified"
    assert profile["payee_new_payers_24h"] == 0
    assert profile["payee_reports_prior"] == 0

    # Verify persistent presence in SQLite payees table
    from api.db.connection import get_db
    with get_db(store.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT vpa, first_seen_at, verified FROM payees WHERE vpa = ?;", (unique_vpa,))
        row = cursor.fetchone()
        assert row is not None
        assert row["vpa"] == unique_vpa
        assert row["verified"] == 0
        assert row["first_seen_at"] is not None


# -----------------------------------------------------------------------------
# Test (e): Link entry with bad domain sets link_bad, failed lookup gives None
# -----------------------------------------------------------------------------
def test_e_link_entry_bad_domain_and_failed_lookup_semantics(demo_test_client):
    """
    Test (e):
    1. Known bad domain sets link_bad=1 and link_domain_age_days.
    2. Unknown / failed domain lookup returns None (unknown), NEVER a safe default (like 0).
    3. Non-link entry channel passes None.
    """
    client, store, _ = demo_test_client

    # 1. Direct domain intel lookup check
    bad_intel = lookup_domain("kyc-verification-desk.top")
    assert bad_intel["bad"] == 1
    assert bad_intel["age_days"] == 4

    legit_intel = lookup_domain("hdfcbank.com")
    assert legit_intel["bad"] == 0
    assert legit_intel["age_days"] == 7300

    unknown_intel = lookup_domain("completely-nonexistent-domain-404xyz.top")
    assert unknown_intel["bad"] is None, "Unknown domain must return None, NEVER a safe default"
    assert unknown_intel["age_days"] is None

    # 2. Endpoint check: Link entry channel with bad domain
    bad_link_payload = {
        "txn_ref": "t-link-bad-01",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "unknown-kyc-desk@ybl",
        "amount": 15000.0,
        "entry_channel": "deep_link_sms",
        "session": {"on_call": True},
        "context": {
            "link_domain": "kyc-verification-desk.top",
            "note_intent": "kyc"
        }
    }
    resp_bad = client.post("/v1/risk/assess", json=bad_link_payload)
    assert resp_bad.status_code == 200
    case_bad = store.get_case(resp_bad.json()["case_id"])
    import json
    feats_bad = json.loads(case_bad["feature_vector"])
    assert feats_bad["link_bad"] == 1
    assert feats_bad["link_domain_age_days"] == 4.0

    # 3. Endpoint check: Link entry channel with unknown domain -> None (never safe 0)
    unknown_link_payload = {
        "txn_ref": "t-link-unknown-01",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "random-payee@okaxis",
        "amount": 2500.0,
        "entry_channel": "deep_link_whatsapp",
        "session": {"on_call": False},
        "context": {
            "link_domain": "unregistered-test-portal-889.xyz"
        }
    }
    resp_unk = client.post("/v1/risk/assess", json=unknown_link_payload)
    assert resp_unk.status_code == 200
    case_unk = store.get_case(resp_unk.json()["case_id"])
    feats_unk = json.loads(case_unk["feature_vector"])
    assert feats_unk["link_bad"] is None, "Failed lookup must record None, never safe default"

    # 4. Endpoint check: Non-link entry channel -> None
    typed_payload = {
        "txn_ref": "t-typed-01",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "rahul.sharma@oksbi",
        "amount": 200.0,
        "entry_channel": "typed_vpa"
    }
    resp_typed = client.post("/v1/risk/assess", json=typed_payload)
    assert resp_typed.status_code == 200
    case_typed = store.get_case(resp_typed.json()["case_id"])
    feats_typed = json.loads(case_typed["feature_vector"])
    assert feats_typed["link_bad"] is None
    assert feats_typed["link_domain_age_days"] is None
