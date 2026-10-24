"""Analyst console: payee view, clear endpoint and the page itself."""
from fastapi.testclient import TestClient

from api.main import app


def _pay(client, user, vpa, amount=2000.0):
    case = client.post("/v1/risk/assess", json={"user_ref": user, "payee_vpa": vpa, "amount": amount,
                                                "session": {"on_call": False}}).json()
    return client.post("/v1/payments/complete", json={"case_id": case["case_id"], "user_ref": user,
                                                      "payee_vpa": vpa, "amount": amount})


def test_payee_view_shows_the_fan_in_cluster(client: TestClient):
    vpa = "console-burst-test@ybl"
    for i in range(4):
        assert _pay(client, f"burst-test-{i}@ybl", vpa).status_code == 200
    p = client.get(f"/v1/payees/{vpa}").json()
    assert [x["payer_id"] for x in p["new_payers_24h"]] == [f"burst-test-{i}@ybl" for i in range(4)]
    assert len(p["recent_cases"]) == 4
    assert p["is_confirmed_scam"] is False


def test_clear_withdraws_confirmations_and_is_audited(client: TestClient):
    vpa = "console-clear-test@ybl"
    client.post(f"/v1/payees/{vpa}/confirm", json={"analyst_id": "analyst_alpha"})
    client.post(f"/v1/payees/{vpa}/confirm", json={"analyst_id": "analyst_beta"})
    assess = {"user_ref": "raksham@oksbi", "payee_vpa": vpa, "amount": 500.0, "session": {"on_call": False}}
    assert client.post("/v1/risk/assess", json=assess).json()["tier"] == "decline"

    r = client.post(f"/v1/payees/{vpa}/clear", json={"analyst_id": "analyst_gamma", "notes": "false alarm"})
    assert r.status_code == 200
    assert r.json()["withdrawn_confirmations"] == ["analyst_alpha", "analyst_beta"]
    assert client.post("/v1/risk/assess", json=assess).json()["tier"] != "decline"
    assert client.get(f"/v1/payees/{vpa}").json()["confirmations"] == []
    assert client.get("/health").json()["status"] == "ok"  # the audit chain still verifies


def test_analyst_endpoints_need_the_key(client: TestClient):
    with TestClient(app) as anon:
        assert anon.get("/v1/payees/x@ybl").status_code == 401
        assert anon.post("/v1/payees/x@ybl/clear", json={"analyst_id": "a"}).status_code == 401
        page = anon.get("/console")  # the page itself is public; its data calls carry the key
        assert page.status_code == 200 and "Satark analyst console" in page.text
