"""Appeals (plan 4.2): "This was me" on amber; red and decline only go to an analyst."""
from fastapi.testclient import TestClient


def _assess(client, user, vpa, amount, on_call=False):
    return client.post("/v1/risk/assess", json={"user_ref": user, "payee_vpa": vpa, "amount": amount,
                                                "session": {"on_call": on_call}}).json()


def _rules(client, case_id):
    return client.get(f"/v1/cases/{case_id}").json()["evidence_pack"].get("applied_rules", [])


def test_this_was_me_lowers_later_ambers_but_not_during_a_call(client: TestClient):
    user, vpa = "appeal-amber@ybl", "kirana-store@paytm"
    first = _assess(client, user, vpa, 3000)
    assert first["tier"] == "amber"
    r = client.post(f"/v1/risk/{first['case_id']}/appeal", json={"user_ref": user})
    assert r.json()["status"] == "payee_trusted"
    assert client.get(f"/v1/cases/{first['case_id']}").json()["dispute"] == "this_was_me"

    later = _assess(client, user, vpa, 3000)
    assert later["tier"] == "green" and "user_vouched_payee_green" in _rules(client, later["case_id"])
    on_call = _assess(client, user, vpa, 3000, on_call=True)
    assert "user_vouched_payee_green" not in _rules(client, on_call["case_id"])


def test_red_has_no_instant_appeal_and_waits_for_an_analyst(client: TestClient):
    user, vpa = "appeal-red@ybl", "amaz0n-refund-desk@okaxis"
    red = _assess(client, user, vpa, 3000)
    assert red["tier"] == "red"
    assert client.post(f"/v1/risk/{red['case_id']}/appeal", json={"user_ref": user}).status_code == 409

    r = client.post(f"/v1/risk/{red['case_id']}/false-alarm", json={"user_ref": user})
    assert r.json()["status"] == "sent_for_review"
    assert _assess(client, user, vpa, 3000)["tier"] == "red"  # nothing changes yet

    ok = client.post(f"/v1/cases/{red['case_id']}/accept-appeal", json={"analyst_id": "analyst_alpha"})
    assert ok.status_code == 200
    assert _assess(client, user, vpa, 3000)["tier"] == "green"
    assert _assess(client, "someone-else@ybl", vpa, 3000)["tier"] == "red"  # only this user and payee


def test_declined_payee_stays_declined_after_an_accepted_appeal(client: TestClient):
    user, vpa = "appeal-decline@ybl", "confirmed-scam-mule@ybl"
    dec = _assess(client, user, vpa, 2000)
    assert dec["tier"] == "decline"
    client.post(f"/v1/risk/{dec['case_id']}/false-alarm", json={"user_ref": user})
    assert client.post(f"/v1/cases/{dec['case_id']}/accept-appeal",
                       json={"analyst_id": "analyst_alpha"}).json()["payee_still_declined"] is True
    assert _assess(client, user, vpa, 2000)["tier"] == "decline"


def test_only_the_case_owner_can_appeal(client: TestClient):
    case = _assess(client, "owner@ybl", "kirana-store@paytm", 3000)
    assert client.post(f"/v1/risk/{case['case_id']}/appeal", json={"user_ref": "intruder@ybl"}).status_code == 403
