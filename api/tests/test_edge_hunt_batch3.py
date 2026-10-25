"""
Regression tests for the edge-case hunt, batch 3: one clock for payment hours, reports override the
verified badge, payments completed exactly once, and per-analyst keys.
"""

import os
import threading
import time

from fastapi.testclient import TestClient

from api.main import app
from api.policy.engine import PolicyEngine
from api.routers.assess import get_feature_store


def _assess(client, user, payee, amount):
    r = client.post("/v1/risk/assess", json={"user_ref": user, "payee_vpa": payee, "amount": amount})
    assert r.status_code == 200, r.text
    return r.json()


def test_stored_and_scored_hours_use_one_clock_whatever_the_server_timezone(client: TestClient):
    from api.store.sqlite_store import local_hour
    store = app.dependency_overrides[get_feature_store]()
    old = os.environ.get("TZ")
    try:
        for tz in ("UTC", "America/New_York", "Asia/Kolkata"):
            os.environ["TZ"] = tz
            time.tzset()
            user = f"b3-clock-{tz.replace('/', '-').lower()}@ybl"
            store.record_payment(payer_id=user, payee_vpa="chaipoint@icici", amount=200.0)
            from api.db.connection import get_db
            with get_db(store.db_path) as conn:
                stored = conn.execute("SELECT hour FROM transactions WHERE user_id = ?", (user,)).fetchone()["hour"]
            scored = store.compute_baseline_features(user, "chaipoint@icici", 200.0)["hour"]
            assert stored == scored == local_hour(), tz
    finally:
        if old is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old
        time.tzset()


class _Fixed:
    thr = {"amber": 0.856, "red": 0.9964}

    def score(self, *a, **k):
        return {"fusion_score": 0.1, "reasons": [], "tier_hint": None}


def test_a_reported_verified_merchant_loses_its_exemptions():
    engine = PolicyEngine(scorer=_Fixed())
    f = {"payee_verified": True, "payee_first_time": True, "amount": 30000, "amount_ratio": 1.0,
         "payee_new_payers_24h": 300}
    assert engine.evaluate(f).tier == "green"
    reported = {**f, "payee_reports_prior": 2}
    assert "large_first_payment_to_stranger" in engine.evaluate(reported).applied_rules
    assert engine.compute_family_contributions(reported)["B"] > engine.compute_family_contributions(f)["B"]


def test_a_payment_is_completed_exactly_once_under_concurrent_requests(client: TestClient):
    store = app.dependency_overrides[get_feature_store]()
    case = _assess(client, "b3-race@ybl", "b3-race-payee@ybl", 300)
    wins = []
    threads = [threading.Thread(target=lambda: wins.append(store.claim_completion(case["case_id"]))) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert wins.count(True) == 1

    # A concurrent evidence update (a report or questionnaire landing) keeps the completed flag.
    for i in range(10):
        c = _assess(client, "b3-race@ybl", f"b3-race-{i}@ybl", 300)
        row = store.get_case(c["case_id"])
        t1 = threading.Thread(target=store.claim_completion, args=(c["case_id"],))
        t2 = threading.Thread(target=store.update_case_decision,
                              args=(c["case_id"], row["tier"], [], row["template_id"], 0, {"questionnaire_rules": []}))
        t1.start(); t2.start(); t1.join(); t2.join()
        assert client.get(f"/v1/cases/{c['case_id']}").json()["status"] == "completed"


def test_per_analyst_keys_make_two_confirmations_mean_two_people(client: TestClient, monkeypatch):
    monkeypatch.setenv("SATARK_ANALYST_KEYS", "alice:k-alice-123,bob:k-bob-456")
    vpa = "b3-two-people@ybl"
    with TestClient(app) as anon:
        shared = anon.post(f"/v1/payees/{vpa}/confirm", json={"analyst_id": "x"},
                           headers={"X-API-Key": os.environ["SATARK_ANALYST_KEY"]})
        assert shared.status_code == 401  # the shared key no longer works
        assert anon.get("/v1/cases", headers={"X-API-Key": "pröbe".encode("latin-1")}).status_code == 401  # not a 500
        alice = {"X-API-Key": "k-alice-123"}
        # One key, two typed names: still one analyst.
        anon.post(f"/v1/payees/{vpa}/confirm", json={"analyst_id": "alice"}, headers=alice)
        r = anon.post(f"/v1/payees/{vpa}/confirm", json={"analyst_id": "someone_else"}, headers=alice).json()
        assert (r["analyst_id"], r["is_confirmed_scam"]) == ("alice", False)
        r = anon.post(f"/v1/payees/{vpa}/confirm", json={}, headers={"X-API-Key": "k-bob-456"}).json()
        assert r["is_confirmed_scam"] is True


def test_a_blank_analyst_id_is_refused_with_the_shared_key(client: TestClient):
    r = client.post("/v1/payees/b3-blank@ybl/confirm", json={"analyst_id": "  "})
    assert r.status_code == 422
