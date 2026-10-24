"""A large first payment to someone who is not a saved contact gets an amber warning."""
from fastapi.testclient import TestClient


def _assess(client, user, vpa, amount, channel):
    r = client.post("/v1/risk/assess", json={"user_ref": user, "payee_vpa": vpa, "amount": amount,
                                             "entry_channel": channel, "session": {"on_call": False}}).json()
    return r, client.get(f"/v1/cases/{r['case_id']}").json()["evidence_pack"]


def test_large_first_payment_to_an_unknown_number_warns(client: TestClient):
    r, ev = _assess(client, "raksham@oksbi", "5656565656@oksbi", 50000, "typed_vpa")
    assert r["tier"] in ("amber", "red")
    assert "AMOUNT_UNUSUAL" in r["reasons"] and "NEW_PAYEE" in r["reasons"]


def test_not_for_contacts_small_amounts_or_verified_merchants(client: TestClient):
    _, ev = _assess(client, "raksham@oksbi", "5757575757@oksbi", 50000, "contact")
    assert "large_first_payment_to_stranger" not in ev["applied_rules"]
    _, ev = _assess(client, "raksham@oksbi", "5858585858@oksbi", 5000, "typed_vpa")
    assert "large_first_payment_to_stranger" not in ev["applied_rules"]
    _, ev = _assess(client, "raksham@oksbi", "zomato@hdfcbank", 50000, "typed_vpa")
    assert "large_first_payment_to_stranger" not in ev["applied_rules"]


def test_unknown_entry_channel_is_scored_as_typed(client: TestClient):
    _, ev = _assess(client, "raksham@oksbi", "5959595959@oksbi", 300, "phone_number")
    assert ev["features"]["entry_channel"] == "typed_vpa"
