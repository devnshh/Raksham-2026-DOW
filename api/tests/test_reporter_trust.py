"""Reporter-trust weighting (plan 4.3): reports count by the reporter's history."""
from fastapi.testclient import TestClient

from api.store.sqlite_store import reporter_weight


def _report(client, reporter, vpa):
    return client.post("/v1/report", json={"reporter_id": reporter, "payee_vpa": vpa, "reason": "scam"})


def _reports_prior(client, vpa):
    case = client.post("/v1/risk/assess", json={"user_ref": "raksham@oksbi", "payee_vpa": vpa, "amount": 120.0,
                                                "session": {"on_call": False}}).json()
    return case, client.get(f"/v1/cases/{case['case_id']}").json()["evidence_pack"]["features"]["payee_reports_prior"]


def test_twenty_fresh_accounts_cannot_flag_an_honest_merchant(client: TestClient):
    vpa = "chaipoint@icici"
    for i in range(20):
        assert _report(client, f"sockpuppet-{i:02d}@ybl", vpa).status_code == 200
    case, reports = _reports_prior(client, vpa)
    assert reports == 0
    assert case["tier"] == "green"


def test_an_established_reporter_counts_in_full(client: TestClient):
    vpa = "trust-test-payee@ybl"
    _report(client, "raksham@oksbi", vpa)  # seeded: account about 13 months old, many payments
    assert _reports_prior(client, vpa)[1] == 1


def test_weights():
    assert reporter_weight(0, 0) == 0
    assert reporter_weight(400, 12) == 1
    assert reporter_weight(15, 5) == 0.5
