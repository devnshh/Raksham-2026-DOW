"""
Regression tests for the edge-case hunt, batch 2 (each change chosen on validation world 33 and confirmed
on 44 and 55): notes never lower risk, bad links always warn, whole-word note keywords, screen sharing on
an established payee, the stranger floor after a first payment, the unknown-caller rule, the vouch cap,
and collect requests.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from api.db.connection import get_db
from api.main import app
from api.policy.engine import PolicyEngine
from api.policy.intent import resolve_note_intent
from api.policy.scorer import get_satark_scorer
from api.routers.assess import get_feature_store


class _Fixed:
    """A scorer with a set fusion score, on the deployed thresholds."""
    thr = {"amber": 0.856, "red": 0.9964}

    def __init__(self, s):
        self.s = s

    def score(self, *a, **k):
        return {"fusion_score": self.s, "reasons": [], "tier_hint": None}


def _assess(client, user, payee, amount, entry="typed_vpa", session=None, context=None):
    r = client.post("/v1/risk/assess", json={"user_ref": user, "payee_vpa": payee, "amount": amount,
                                             "entry_channel": entry, "session": session or {},
                                             "context": context or {}})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_note_never_scores_lower_than_no_note(client: TestClient):
    case = _assess(client, "b2-note@ybl", "b2-note-payee@ybl", 5000)
    features = client.get(f"/v1/cases/{case['case_id']}").json()["evidence_pack"]["features"]
    scorer = get_satark_scorer()
    empty = scorer.score(features, note_intent="none")["fusion_score"]
    for benign in ("home", "food", "family"):
        assert scorer.score(features, note_intent=benign)["fusion_score"] >= empty, benign


def test_a_known_bad_link_always_warns_including_subdomains(client: TestClient):
    for domain in ("sbi-refund-portal.xyz", "www.sbi-refund-portal.xyz", "pay.sbi-refund-portal.xyz."):
        case = _assess(client, "b2-link@ybl", f"b2-{len(domain)}@ybl", 499, entry="deep_link_sms",
                       context={"link_domain": domain, "note_intent": "home"})
        assert case["tier"] in ("amber", "red"), domain


def test_note_keywords_are_whole_words_and_scam_stories_win():
    assert resolve_note_intent(None, "refund for parents") == "refund"
    assert resolve_note_intent(None, "digital arrest current account") == "legal"
    for honest in ("money received thanks", "courtyard repair", "multitasking class fee"):
        assert resolve_note_intent(None, honest) == "none", honest
    assert resolve_note_intent(None, "tasks done, refunds pending") == "refund"


def test_screen_sharing_on_an_established_payee_does_not_warn_unless_a_stranger_calls():
    engine = PolicyEngine(scorer=_Fixed(0.01))
    base = {"screen_shared": True, "payee_first_time": False, "amount_ratio": 1.0, "amount": 450}
    assert engine.evaluate(base, trusted_payee_history=(2, 10)).tier == "green"
    assert engine.evaluate(base, trusted_payee_history=(1, 0)).tier == "amber"  # a same-day first payment
    stranger_call = {**base, "on_call": True, "caller_in_contacts": False}
    assert engine.evaluate(stranger_call, trusted_payee_history=(2, 10)).tier == "amber"


def test_the_stranger_floor_still_applies_after_a_small_first_payment():
    engine = PolicyEngine(scorer=_Fixed(0.05))
    after_rs1 = {"payee_first_time": False, "amount": 50000, "amount_ratio": 1.0}
    d = engine.evaluate(after_rs1, trusted_payee_history=(1, 0))
    assert "large_first_payment_to_stranger" in d.applied_rules
    split = {"payee_first_time": False, "amount": 15000, "same_payee_sum_24h": 15000, "amount_ratio": 1.0}
    assert "large_first_payment_to_stranger" in engine.evaluate(split, trusted_payee_history=(1, 0)).applied_rules
    assert engine.evaluate(after_rs1, trusted_payee_history=(6, 90)).tier == "green"  # trusted payee


def test_unknown_caller_with_a_large_payment_to_a_new_payee_warns():
    engine = PolicyEngine(scorer=_Fixed(0.75))
    f = {"on_call": True, "caller_in_contacts": False, "payee_first_time": True, "amount": 9000, "amount_ratio": 5.0}
    assert "unknown_caller_new_payee" in engine.evaluate(f).applied_rules
    assert engine.evaluate({**f, "caller_in_contacts": True}).tier == "green"
    assert PolicyEngine(scorer=_Fixed(0.5)).evaluate(f).tier == "green"


def test_this_was_me_covers_about_the_vouched_amount_only():
    engine = PolicyEngine(scorer=_Fixed(0.9))
    f = {"payee_first_time": True, "amount_ratio": 3.0}
    assert engine.evaluate({**f, "amount": 40000}, pair_trust="user", vouched_amount=30000).tier == "green"
    assert engine.evaluate({**f, "amount": 95000}, pair_trust="user", vouched_amount=30000).tier == "amber"
    assert engine.evaluate({**f, "amount": 30000, "note_intent": "kyc"}, pair_trust="user",
                           vouched_amount=30000).tier == "amber"
    # Fails closed without a vouched amount, and splitting within 24 hours counts together.
    assert engine.evaluate({**f, "amount": 1000}, pair_trust="user", vouched_amount=None).tier == "amber"
    assert engine.evaluate({**f, "amount": 30000, "same_payee_sum_24h": 30000}, pair_trust="user",
                           vouched_amount=30000).tier == "amber"


def test_this_was_me_is_refused_on_an_old_warning(client: TestClient):
    user = "b2-old-vouch@ybl"
    amber = _assess(client, user, "b2-old-vouch-payee@ybl", 30000)
    assert amber["tier"] == "amber"
    store = app.dependency_overrides[get_feature_store]()
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    with get_db(store.db_path) as conn:
        conn.execute("UPDATE cases SET created_at = ? WHERE case_id = ?", (old, amber["case_id"]))
    assert client.post(f"/v1/risk/{amber['case_id']}/appeal", json={"user_ref": user}).status_code == 409


def test_a_collect_request_with_a_receive_story_warns():
    engine = PolicyEngine(scorer=_Fixed(0.05))
    f = {"entry_channel": "merchant_collect", "payee_first_time": True, "amount": 4999, "note_intent": "receive"}
    d = engine.evaluate(f)
    assert d.tier == "amber" and d.reasons[0] == "COLLECT_REQUEST"
    assert engine.evaluate({**f, "payee_verified": True}).tier == "green"
    assert engine.evaluate({**f, "note_intent": "food"}).tier == "green"
