"""
Regression tests for the edge-case hunt, batch 1: the red pause covers retries, analyst hold release,
completion after an analyst decline, the contact-channel exemption, shortcuts that skipped the model,
fail-open scoring, and input validation.
"""

import time

from fastapi.testclient import TestClient

from api.main import app
from api.policy.engine import PolicyEngine
from api.policy.scorer import get_satark_scorer
from api.routers.assess import get_feature_store

RED_PAYEE = "amaz0n-refund-desk@okaxis"  # seeded reported mule: red at Rs 3,000 with no call


def _assess(client, user, payee, amount, entry="typed_vpa", **session):
    r = client.post("/v1/risk/assess", json={"user_ref": user, "payee_vpa": payee, "amount": amount,
                                             "entry_channel": entry, "session": session})
    assert r.status_code == 200, r.text
    return r.json()


def _complete(client, case, user, payee, amount):
    return client.post("/v1/payments/complete", json={"case_id": case["case_id"], "user_ref": user,
                                                      "payee_vpa": payee, "amount": amount})


def _rules(client, case_id):
    return client.get(f"/v1/cases/{case_id}").json()["evidence_pack"].get("applied_rules", [])


def test_a_retry_returns_the_running_red_pause(client: TestClient):
    user = "edge-retry@ybl"
    red = _assess(client, user, RED_PAYEE, 3000, on_call=True, screen_shared=True)
    assert red["tier"] == "red"
    # "Cut the call, scan my QR instead": same payee, clean session, another channel and amount.
    retry = _assess(client, user, RED_PAYEE, 2500, entry="qr_scan")
    assert (retry["tier"], retry["case_id"]) == ("red", red["case_id"])
    assert 1 <= retry["hold_minutes"] <= 30
    assert _complete(client, red, user, RED_PAYEE, 3000).status_code == 409
    # Another user paying the same payee gets their own check.
    assert _assess(client, "edge-other@ybl", RED_PAYEE, 3000)["case_id"] != red["case_id"]


def test_an_analyst_can_release_the_hold_and_the_next_check_is_fresh(client: TestClient):
    user = "edge-release@ybl"
    red = _assess(client, user, RED_PAYEE, 3000)
    case = client.get(f"/v1/cases/{red['case_id']}").json()
    assert case["hold_active"] is True
    with TestClient(app) as anonymous:
        assert anonymous.post(f"/v1/cases/{red['case_id']}/release", json={"analyst_id": "a"}).status_code == 401
    assert client.post(f"/v1/cases/{red['case_id']}/release", json={"analyst_id": " "}).status_code == 422
    r = client.post(f"/v1/cases/{red['case_id']}/release", json={"analyst_id": "analyst_alpha"})
    assert r.status_code == 200
    assert client.get(f"/v1/cases/{red['case_id']}").json()["hold_active"] is False
    assert client.post(f"/v1/cases/{red['case_id']}/release", json={"analyst_id": "analyst_alpha"}).status_code == 409
    assert _complete(client, red, user, RED_PAYEE, 3000).status_code == 200
    assert _assess(client, user, RED_PAYEE, 3000)["case_id"] != red["case_id"]


def test_this_was_me_is_refused_after_a_red_pause_on_the_payee(client: TestClient):
    user, payee = "edge-vouch@ybl", "edge-vouch-payee@ybl"
    amber = _assess(client, user, payee, 30000)  # large first payment to a stranger
    assert amber["tier"] == "amber"
    store = app.dependency_overrides[get_feature_store]()
    store.record_case("c-edge-red", None, user, payee, 30000, "red", ["ON_CALL"], "red_call_new_payee_v1", 30, {}, {})
    r = client.post(f"/v1/risk/{amber['case_id']}/appeal", json={"user_ref": user})
    assert r.status_code == 409


def test_payment_to_a_payee_declined_after_the_check_is_refused(client: TestClient):
    user, payee = "edge-race@ybl", "edge-race-payee@ybl"
    case = _assess(client, user, payee, 500)
    assert case["tier"] == "green"
    for analyst in ("analyst_alpha", "analyst_beta"):
        client.post(f"/v1/payees/{payee}/confirm", json={"analyst_id": analyst})
    assert _complete(client, case, user, payee, 500).status_code == 403


def test_contact_channel_is_not_exempt_on_an_unknown_call(client: TestClient):
    user = "edge-contact@ybl"
    plain = _assess(client, user, "edge-saved-today@ybl", 50000, entry="contact")
    assert "large_first_payment_to_stranger" not in _rules(client, plain["case_id"])
    on_call = _assess(client, user, "edge-saved-today2@ybl", 50000, entry="contact", on_call=True)
    assert on_call["tier"] in ("amber", "red")
    assert "large_first_payment_to_stranger" in _rules(client, on_call["case_id"]) or on_call["tier"] == "red"


def _trusted(engine, **features):
    base = {"payee_first_time": False, "amount_ratio": 1.0, "escalation_ratio": 1.0, "payee_reports_prior": 0}
    return engine.evaluate({**base, **features}, trusted_payee_history=(6, 60)).applied_rules


def test_trust_does_not_cover_reports_bad_links_or_big_jumps(policy_engine: PolicyEngine):
    assert _trusted(policy_engine) == ["trusted_payee_silent_pass"]
    for risky in ({"payee_reports_prior": 2}, {"link_bad": 1}, {"escalation_ratio": 50.0}):
        assert "trusted_payee_bypassed_by_risk" in _trusted(policy_engine, **risky), risky


def test_gate_sends_reported_payees_bad_links_and_scam_notes_to_the_model(policy_engine: PolicyEngine):
    base = {"payee_first_time": False, "amount_ratio": 1.0}
    assert "eligibility_gate_silent_pass" in policy_engine.evaluate(base).applied_rules
    for risky in ({"payee_reports_prior": 1}, {"link_bad": 1}, {"note_intent": "task"}):
        assert "eligibility_gate_passed" in policy_engine.evaluate({**base, **risky}).applied_rules, risky


class _Raises:
    def score(self, *a, **k):
        raise RuntimeError("boom")


class _NaN:
    def score(self, *a, **k):
        return {"fusion_score": float("nan"), "reasons": []}


class _Slow:
    def __init__(self):
        self.inner = get_satark_scorer()
        self.thr = self.inner.thr

    def score(self, *a, **k):
        time.sleep(0.35)
        return self.inner.score(*a, **k)


def test_scorer_failure_still_runs_the_checks_that_need_no_model():
    features = {"payee_first_time": True, "amount_ratio": 1.0, "amount": 9999, "payee_reports_prior": 3}
    for scorer in (_Raises(), _NaN()):
        d = PolicyEngine(scorer=scorer).evaluate(features)
        assert "fail_open_device_check" in d.applied_rules
        assert (d.tier, d.reasons) == ("amber", ["PAYEE_REPORTED"])
    stranger = PolicyEngine(scorer=_Raises()).evaluate({"payee_first_time": True, "amount": 40000})
    assert stranger.tier == "amber" and "NEW_PAYEE" in stranger.reasons


def test_a_late_score_is_used_not_discarded(client: TestClient):
    d = PolicyEngine(scorer=_Slow()).evaluate({"payee_first_time": True, "amount_ratio": 1.0, "amount": 100})
    assert "scoring_slow" in d.applied_rules and "fail_open_device_check" not in d.applied_rules


def _report(client, reporter, payee):
    return client.post("/v1/report", json={"reporter_id": reporter, "payee_vpa": payee, "reason": "scam"}).json()


def test_a_real_user_with_history_counts_as_an_established_reporter(client: TestClient):
    from api.db.connection import get_db
    store = app.dependency_overrides[get_feature_store]()
    old_ms = int((time.time() - 40 * 86400) * 1000)
    with get_db(store.db_path) as conn:  # 6 payments over 40 days, and no users row (only seeds create one)
        for i in range(6):
            conn.execute("INSERT INTO transactions (user_id, payee_vpa, amount, hour, timestamp_ms, created_at) "
                         "VALUES (?,?,?,?,?,?)", ("edge-real-user@ybl", "chaipoint@icici", 200.0, 10,
                                                  old_ms + i * 86400000, "2026-09-15T10:00:00+00:00"))
    _assess(client, "edge-real-user@ybl", "edge-mule-a@ybl", 2000)
    assert _report(client, "edge-real-user@ybl", "edge-mule-a@ybl")["prior_reports_count"] == 1


def test_a_report_counts_only_from_someone_who_dealt_with_the_payee(client: TestClient):
    payee = "edge-competitor-target@ybl"
    # An established account that never checked or paid this payee: stored, but adds nothing.
    assert _report(client, "raksham@oksbi", payee)["prior_reports_count"] == 0
    _assess(client, "raksham@oksbi", payee, 400)
    assert _report(client, "raksham@oksbi", payee)["prior_reports_count"] == 1


def test_malformed_payee_and_amount_are_rejected(client: TestClient):
    def status(**overrides):
        body = {"user_ref": "edge-input@ybl", "payee_vpa": "shop@ybl", "amount": 100, **overrides}
        return client.post("/v1/risk/assess", json=body).status_code

    assert status() == 200
    assert status(payee_vpa="  Shop.Owner@OKSBI ") == 200
    for vpa in ("", "@", "rahul", "x@y@z", "a" * 300 + "@ybl", "sbі-kyc@ybl"):
        assert status(payee_vpa=vpa) == 422, vpa
    for amount in (0, -500, 2_000_000):
        assert status(amount=amount) == 422, amount
    nan = client.post("/v1/risk/assess", content='{"user_ref": "u", "payee_vpa": "shop@ybl", "amount": NaN}',
                      headers={"Content-Type": "application/json"})
    assert nan.status_code == 422
    done = client.post("/v1/payments/complete", json={"case_id": "c-x", "user_ref": "u", "payee_vpa": "shop@ybl",
                                                      "amount": 0})
    assert done.status_code == 422


def test_the_phone_sees_an_analyst_release(client: TestClient):
    user = "edge-status@ybl"
    red = _assess(client, user, RED_PAYEE, 3000)
    status = client.post(f"/v1/risk/{red['case_id']}/status", json={"user_ref": user}).json()
    assert status["hold_active"] and 0 < status["hold_seconds_left"] <= 1800 and not status["released"]
    assert client.post(f"/v1/risk/{red['case_id']}/status", json={"user_ref": "someone-else@ybl"}).status_code == 403
    client.post(f"/v1/cases/{red['case_id']}/release", json={"analyst_id": "analyst_alpha"})
    status = client.post(f"/v1/risk/{red['case_id']}/status", json={"user_ref": user}).json()
    assert (status["hold_active"], status["hold_seconds_left"], status["released"], status["status"]) == (False, 0, True, "open")
    assert "analyst" not in str(status)  # who released it is not shown to the user


def test_cancelling_on_the_phone_shows_cancelled_but_keeps_the_pause(client: TestClient):
    user = "edge-cancel@ybl"
    red = _assess(client, user, RED_PAYEE, 3000)
    assert client.post(f"/v1/risk/{red['case_id']}/cancel", json={"user_ref": "someone-else@ybl"}).status_code == 403
    assert client.post(f"/v1/risk/{red['case_id']}/cancel", json={"user_ref": user}).status_code == 200
    case = client.get(f"/v1/cases/{red['case_id']}").json()
    assert (case["status"], case["hold_active"]) == ("cancelled", False)
    # Cancel and try again must not skip the pause: the retry reopens the same paused case.
    retry = _assess(client, user, RED_PAYEE, 3000)
    assert (retry["tier"], retry["case_id"]) == ("red", red["case_id"])
    case = client.get(f"/v1/cases/{red['case_id']}").json()
    assert (case["status"], case["hold_active"]) == ("open", True)
