"""
End-to-End API Integration Tests for SATARK Backend.
Validates the canonical three README demo journeys, analyst flow, and case evidence pack.
"""

from fastapi.testclient import TestClient


def test_journey_1_silent_pass(client: TestClient):
    """
    Demo Journey 1: Silent Pass.
    Pay ₹450 to saved friend (rahul.sharma@oksbi).
    Expected: GREEN tier, hold_minutes=0, template_id='green_silent_pass'.
    Legitimate users experience zero friction.
    """
    payload = {
        "txn_ref": "txn_demo_01",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "rahul.sharma@oksbi",
        "amount": 450.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": False,
            "screen_shared": False,
            "remote_app_present": False,
            "remote_app_new": False,
            "app_switches": 0,
            "typing_ms": 280.0,
            "pauses": 0,
            "pin_secs": 3.2,
            "device_new": False,
            "failed_auth": 0
        },
        "context": {
            "note_text": "dinner split",
            "link_domain": None,
            "secs_link_to_pay": None
        }
    }

    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["tier"] == "green"
    assert data["hold_minutes"] == 0
    assert data["template_id"] in ["green_silent_pass", "green_pass_v1"]
    assert "case_id" in data
    # Strict contract: score and weights are NEVER exposed
    assert "score" not in data
    assert "family_contrib" not in data


def test_journey_2_red_pause_coached_kyc_scam(client: TestClient):
    """
    Demo Journey 2: Red Pause.
    Teammate calls victim as fake 'KYC officer'.
    Pay ₹48,000 to new lookalike handle (kyc-helpdesk-update@ybl).
    Expected: RED tier, hold_minutes=30, corroboration verified with reasons.
    """
    payload = {
        "txn_ref": "txn_demo_02",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "kyc-helpdesk-update@ybl",
        "amount": 48000.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": True,                 # Family A
            "screen_shared": False,
            "remote_app_present": False,
            "remote_app_new": False,
            "app_switches": 3,
            "typing_ms": 420.0,
            "pauses": 3,
            "pin_secs": 8.5,
            "device_new": False,
            "failed_auth": 0
        },
        "context": {
            "note_text": "kyc verification deposit",
            "link_domain": None,
            "secs_link_to_pay": None
        }
    }

    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["tier"] == "red"
    assert data["hold_minutes"] == 30
    assert "ON_CALL" in data["reasons"]
    assert "case_id" in data

    # Verify that case is saved and accessible via analyst endpoint
    case_id = data["case_id"]
    case_resp = client.get(f"/v1/cases/{case_id}")
    assert case_resp.status_code == 200
    case_data = case_resp.json()
    assert case_data["tier"] == "red"
    assert case_data["evidence_pack"] is not None
    assert case_data["evidence_pack"]["features"]["on_call"] is True


def test_journey_3_mule_caught_dual_analyst_confirmation(client: TestClient):
    """
    Demo Journey 3: Mule Caught.
    1st analyst confirms payee -> pending.
    2nd distinct analyst confirms -> takes effect.
    Next payer attempting to transfer -> DECLINE.
    """
    mule_vpa = "new-emerging-mule@ybl"

    # 1. First analyst confirms payee
    resp1 = client.post(
        f"/v1/payees/{mule_vpa}/confirm",
        json={"analyst_id": "analyst_alpha", "notes": "Suspected KYC scam ring"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total_confirmations"] == 1
    assert data1["is_confirmed_scam"] is False
    assert data1["status"] == "pending_second_analyst"

    # 2. Same analyst confirming again does NOT count twice
    resp_dup = client.post(
        f"/v1/payees/{mule_vpa}/confirm",
        json={"analyst_id": "analyst_alpha", "notes": "Duplicate check"}
    )
    assert resp_dup.json()["total_confirmations"] == 1
    assert resp_dup.json()["is_confirmed_scam"] is False

    # 3. Second distinct analyst confirms
    resp2 = client.post(
        f"/v1/payees/{mule_vpa}/confirm",
        json={"analyst_id": "analyst_beta", "notes": "Confirmed mule account"}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total_confirmations"] == 2
    assert data2["is_confirmed_scam"] is True
    assert data2["status"] == "analyst_confirmed_scam"

    # 4. Next payer attempting payment to this mule -> DECLINE
    payment_payload = {
        "txn_ref": "txn_demo_03",
        "user_ref": "raksham@oksbi",
        "payee_vpa": mule_vpa,
        "amount": 2500.0,
        "session": {"on_call": False}
    }
    decline_resp = client.post("/v1/risk/assess", json=payment_payload)
    assert decline_resp.status_code == 200
    decline_data = decline_resp.json()
    assert decline_data["tier"] == "decline"
    assert decline_data["hold_minutes"] == 0
    assert "ANALYST_CONFIRMED_SCAM" in decline_data["reasons"]
    assert decline_data["template_id"] == "decline_known_mule_v1"


def test_user_scam_reporting(client: TestClient):
    """User reports scam payee via POST /v1/report."""
    payee = "reported-fraudster@ybl"
    rep_payload = {
        "reporter_id": "raksham@oksbi",  # an established account: brand-new ones add no weight (plan 4.3)
        "payee_vpa": payee,
        "reason": "Digital arrest scam call",
        "notes": "Claimed to be CBI officer"
    }
    resp = client.post("/v1/report", json=rep_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["prior_reports_count"] >= 1


def test_policy_endpoint(client: TestClient):
    """GET /v1/policy returns active thresholds."""
    resp = client.get("/v1/policy")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "rules" in data
    assert data["rules"]["hold_minutes"] == 30


def test_health_endpoint(client: TestClient):
    """GET /health returns healthy status and intact audit chain."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "healthy"
    assert "intact" in data["audit_chain"]

