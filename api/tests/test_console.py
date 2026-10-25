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
    assert len(p["payments_24h"]) == 4
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


def test_console_summary_counts_the_last_day_and_gives_the_cut_offs(client: TestClient):
    before = client.get("/v1/console/summary").json()["totals"]
    red = client.post("/v1/risk/assess", json={"user_ref": "console-sum@ybl", "payee_vpa": "amaz0n-refund-desk@okaxis",
                                               "amount": 3000.0}).json()
    assert red["tier"] == "red"
    s = client.get("/v1/console/summary").json()
    assert s["totals"]["checks"] == before["checks"] + 1
    assert s["totals"]["red"] == before["red"] + 1 and s["totals"]["holds_running"] >= 1
    assert s["totals"]["money_held"] >= before["money_held"] + 3000
    assert len(s["hourly"]) == 12 and s["hourly"][-1]["red"] >= 1
    assert 0 < s["cutoffs"]["amber"] < s["cutoffs"]["red"] < 1
    assert set(s["family_thresholds"]) == {"A", "B", "C", "D"}


def test_console_payer_amounts_and_font(client: TestClient):
    for amount in (100.0, 300.0, 200.0):
        _pay(client, "console-amounts@ybl", "chaipoint@icici", amount)
    a = client.get("/v1/users/console-amounts@ybl/amounts").json()
    assert sorted(a["amounts"]) == [100.0, 200.0, 300.0] and a["median"] == 200.0
    with TestClient(app) as anon:
        assert anon.get("/v1/console/summary").status_code == 401
        assert anon.get("/v1/users/console-amounts@ybl/amounts").status_code == 401
        font = anon.get("/console/inter.ttf")
        assert font.status_code == 200 and font.headers["content-type"] == "font/ttf"


def test_confirming_a_payee_marks_every_case_to_it(client: TestClient):
    vpa = "console-scam-all@ybl"
    users = [f"console-scam-{i}@ybl" for i in range(5)]
    case_ids = [client.post("/v1/risk/assess", json={"user_ref": u, "payee_vpa": vpa, "amount": 900.0}).json()["case_id"]
                for u in users]
    assert not any(client.get(f"/v1/cases/{c}").json()["payee_confirmed_scam"] for c in case_ids)
    for analyst in ("analyst_alpha", "analyst_beta"):
        client.post(f"/v1/payees/{vpa}/confirm", json={"analyst_id": analyst})
    assert all(client.get(f"/v1/cases/{c}").json()["payee_confirmed_scam"] for c in case_ids)
    listed = {c["case_id"]: c for c in client.get("/v1/cases?limit=100").json()}
    assert all(listed[c]["payee_confirmed_scam"] for c in case_ids if c in listed)
    client.post(f"/v1/payees/{vpa}/clear", json={"analyst_id": "analyst_gamma"})
    assert not client.get(f"/v1/cases/{case_ids[0]}").json()["payee_confirmed_scam"]
