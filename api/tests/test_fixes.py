"""
Regression tests for the review fixes (finale build):
amber cap, single-signal warnings, completion-only payments, server-side holds,
questionnaire, report de-duplication, unknown payee age, truthful reasons,
analyst auth and note-text privacy.
"""

import json

from fastapi.testclient import TestClient

from api.main import app
from api.policy.engine import PolicyEngine
from api.store.sqlite_store import SQLiteFeatureStore


def _assess(client, user, payee, amount, **session):
    payload = {"txn_ref": "t-fix", "user_ref": user, "payee_vpa": payee, "amount": amount,
               "entry_channel": "typed_vpa", "session": session}
    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_two_families_alone_do_not_force_a_warning(policy_engine: PolicyEngine):
    # On a call (A) + first-time payee at 8x the usual amount (D): two families fire, but the score is
    # below the amber threshold. The old "two families means amber" rule is gone (ml/eval_log.md, run 2).
    features = {"on_call": True, "payee_first_time": True, "amount_ratio": 8.0, "amount_z": 3.0}
    decision = policy_engine.evaluate(features)
    assert decision.elevated_families_count >= 2
    assert decision.tier == "green"


def test_a_call_with_a_saved_contact_is_weak_evidence(policy_engine: PolicyEngine):
    unknown = policy_engine.compute_family_contributions({"on_call": True})
    known = policy_engine.compute_family_contributions({"on_call": True, "caller_in_contacts": True})
    assert unknown["A"] >= 0.40 > known["A"]


def test_risk_check_is_not_a_payment_and_completion_is(client: TestClient, test_db_path: str):
    store = SQLiteFeatureStore(test_db_path)
    user, payee = "fix-user-1@oksbi", "fix-new-payee-1@okaxis"
    first = _assess(client, user, payee, 200.0)
    # A risk check records nothing: the payee is still first-time and has no fan-in.
    assert store.compute_baseline_features(user, payee, 200.0)["payee_first_time"] is True
    assert store.get_payee_profile(payee, exclude_payer="someone-else")["payee_new_payers_24h"] == 0

    assert first["tier"] in ("green", "amber"), first
    done = client.post("/v1/payments/complete", json={
        "case_id": first["case_id"], "user_ref": user, "payee_vpa": payee, "amount": 200.0,
        "typing_ms": 300.0, "pauses": 0, "pin_secs": 3.5})
    assert done.status_code == 200 and done.json()["status"] == "recorded"
    again = client.post("/v1/payments/complete", json={
        "case_id": first["case_id"], "user_ref": user, "payee_vpa": payee, "amount": 200.0})
    assert again.json()["status"] == "already_recorded"

    assert store.compute_baseline_features(user, payee, 200.0)["payee_first_time"] is False
    # The payer never counts towards its own payee's fan-in.
    assert store.get_payee_profile(payee, exclude_payer=user)["payee_new_payers_24h"] == 0
    assert store.get_payee_profile(payee, exclude_payer="someone-else")["payee_new_payers_24h"] == 1


def test_completion_refused_for_decline_and_active_red_hold(client: TestClient):
    declined = _assess(client, "fix-user-2@oksbi", "confirmed-scam-mule@ybl", 2000.0)
    assert declined["tier"] == "decline"
    resp = client.post("/v1/payments/complete", json={
        "case_id": declined["case_id"], "user_ref": "fix-user-2@oksbi",
        "payee_vpa": "confirmed-scam-mule@ybl", "amount": 2000.0})
    assert resp.status_code == 403

    red = _assess(client, "raksham@oksbi", "kyc-helpdesk-update@ybl", 48000.0,
                  on_call=True, app_switches=3, typing_ms=420.0, pauses=3)
    assert red["tier"] == "red", red
    resp = client.post("/v1/payments/complete", json={
        "case_id": red["case_id"], "user_ref": "raksham@oksbi",
        "payee_vpa": "kyc-helpdesk-update@ybl", "amount": 48000.0})
    assert resp.status_code == 409


def test_questionnaire_raises_but_never_lowers(client: TestClient):
    user = "fix-user-3@oksbi"
    amber = _assess(client, user, "rahul.sharma@oksbi", 300.0, screen_shared=True)
    assert amber["tier"] == "amber", amber

    wrong_user = client.post(f"/v1/risk/{amber['case_id']}/questionnaire",
                             json={"user_ref": "someone-else", "answers": {"is_anyone_guiding_you": True}})
    assert wrong_user.status_code == 403

    raised = client.post(f"/v1/risk/{amber['case_id']}/questionnaire",
                         json={"user_ref": user, "answers": {"is_anyone_guiding_you": True}}).json()
    assert raised["tier"] == "red" and raised["hold_minutes"] == 30
    assert "USER_REPORTED_GUIDANCE" in raised["reasons"]

    kept = client.post(f"/v1/risk/{amber['case_id']}/questionnaire",
                       json={"user_ref": user, "answers": {"is_anyone_guiding_you": False}}).json()
    assert kept["tier"] == "red"


def test_reports_count_once_per_reporter(client: TestClient):
    payee = "fix-reported-payee@ybl"
    # Seeded established accounts: brand-new reporters add no weight (plan 4.3, tested separately).
    body = {"reporter_id": "default_user", "payee_vpa": payee, "reason": "scam call"}
    assert client.post("/v1/report", json=body).json()["prior_reports_count"] == 1
    assert client.post("/v1/report", json=body).json()["prior_reports_count"] == 1
    body["reporter_id"] = "u-hash-9f2c"
    assert client.post("/v1/report", json=body).json()["prior_reports_count"] == 2


def test_unknown_payee_age_and_reasons_are_truthful(client: TestClient):
    result = _assess(client, "fix-user-4@oksbi", "fix-fresh-payee-4@ybl", 48000.0, on_call=True)
    assert "NEW_PAYEE_YOUNG_ACCOUNT" not in result["reasons"]
    # Entry was a typed UPI ID: a QR or link reason would be false.
    assert "QR_ENTRY" not in result["reasons"] and "LINK_ENTRY" not in result["reasons"]
    case = client.get(f"/v1/cases/{result['case_id']}").json()
    assert case["evidence_pack"]["payee_age_known"] is False


def test_raw_note_text_is_never_stored(client: TestClient):
    payload = {"txn_ref": "t-note", "user_ref": "fix-user-5@oksbi", "payee_vpa": "fix-note-payee@ybl",
               "amount": 5000.0, "context": {"note_text": "secret note about kyc"}}
    result = client.post("/v1/risk/assess", json=payload).json()
    case = client.get(f"/v1/cases/{result['case_id']}").json()
    stored = json.dumps(case)
    assert "secret note" not in stored
    assert case["evidence_pack"]["features"]["note_intent"] == "kyc"


def test_analyst_routes_require_the_key():
    with TestClient(app) as anonymous:
        assert anonymous.get("/v1/cases").status_code == 401
        assert anonymous.post("/v1/payees/x@ybl/confirm", json={"analyst_id": "a"}).status_code == 401
        assert anonymous.post("/internal/scam-registry", json={"vpa": "x@ybl"}).status_code == 401
