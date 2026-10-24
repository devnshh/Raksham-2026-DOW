"""
Unit tests for PolicyEngine (Pure Python, NO FastAPI dependencies).
Tests at least 15 distinct cases covering all rules and invariants.
"""

import pytest
from api.policy.engine import PolicyEngine


def test_analyst_confirmed_scam_declines(policy_engine: PolicyEngine):
    """Rule 1: Analyst-confirmed scam payee -> DECLINE."""
    features = {
        "on_call": False,
        "payee_first_time": False,
        "amount": 100.0,
        "amount_ratio": 1.0
    }
    decision = policy_engine.evaluate(features, is_confirmed_scam_payee=True)
    assert decision.tier == "decline"
    assert decision.hold_minutes == 0
    assert "ANALYST_CONFIRMED_SCAM" in decision.reasons
    assert decision.template_id == "decline_known_mule_v1"
    assert "analyst_confirmed_decline" in decision.applied_rules


def test_trusted_payee_skips_scoring_silent_pass(policy_engine: PolicyEngine):
    """Rule 2: Trusted payee (3+ payments over 30+ days) skips scoring and passes GREEN."""
    features = {
        "on_call": False,
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "payee_first_time": False,
        "amount": 5000.0,
        "amount_ratio": 3.5  # High amount ratio, but trusted payee
    }
    trusted_history = (5, 45)  # 5 payments over 45 days
    decision = policy_engine.evaluate(
        features,
        trusted_payee_history=trusted_history
    )
    assert decision.tier == "green"
    assert decision.template_id == "green_silent_pass"
    assert "trusted_payee_silent_pass" in decision.applied_rules


def test_trusted_payee_bypassed_when_on_call(policy_engine: PolicyEngine):
    """Rule 2 Exception: If Family A fires (e.g. on_call), trusted payee exemption is bypassed."""
    features = {
        "on_call": True,
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "payee_first_time": False,
        "amount": 5000.0,
        "amount_ratio": 1.0
    }
    trusted_history = (10, 60)
    decision = policy_engine.evaluate(
        features,
        trusted_payee_history=trusted_history
    )
    assert "trusted_payee_bypassed_by_family_a" in decision.applied_rules
    # Scoring executed (no silent pass). Being on a call is a single weak signal, so paying a
    # trusted payee at a normal amount stays green (changed: it used to warn on every call).
    assert "eligibility_gate_passed" in decision.applied_rules
    assert decision.tier == "green"


def test_trusted_payee_bypassed_when_screen_shared(policy_engine: PolicyEngine):
    """Rule 2 Exception: Screen sharing bypasses trusted payee exemption."""
    features = {
        "on_call": False,
        "screen_shared": True,
        "remote_app_present": False,
        "remote_app_new": False,
        "payee_first_time": False,
        "amount": 200.0,
        "amount_ratio": 0.5
    }
    trusted_history = (4, 35)
    decision = policy_engine.evaluate(
        features,
        trusted_payee_history=trusted_history
    )
    assert "trusted_payee_bypassed_by_family_a" in decision.applied_rules


def test_eligibility_gate_silent_pass_normal_amount(policy_engine: PolicyEngine):
    """Rule 3: Known payee with normal amount and no coercion passes GREEN silently."""
    features = {
        "on_call": False,
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "payee_first_time": False,
        "amount_ratio": 1.2,  # < 2.0
        "lookalike_score": 0.0
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "green"
    assert decision.template_id == "green_silent_pass"
    assert "eligibility_gate_silent_pass" in decision.applied_rules


def test_eligibility_gate_fires_on_first_time_payee(policy_engine: PolicyEngine):
    """Rule 3: First-time payee passes eligibility gate to be scored."""
    features = {
        "on_call": False,
        "screen_shared": False,
        "payee_first_time": True,
        "payee_age_days": 180.0,
        "amount_ratio": 1.0,
        "lookalike_score": 0.0
    }
    decision = policy_engine.evaluate(features)
    assert "eligibility_gate_passed" in decision.applied_rules


def test_eligibility_gate_fires_on_high_amount_ratio(policy_engine: PolicyEngine):
    """Rule 3: Known payee with amount_ratio >= 2.0 passes eligibility gate."""
    features = {
        "on_call": False,
        "screen_shared": False,
        "payee_first_time": False,
        "amount_ratio": 2.5,
        "lookalike_score": 0.0
    }
    decision = policy_engine.evaluate(features)
    assert "eligibility_gate_passed" in decision.applied_rules


def test_eligibility_gate_fires_on_lookalike_handle(policy_engine: PolicyEngine):
    """Rule 3: High lookalike score passes eligibility gate."""
    features = {
        "on_call": False,
        "screen_shared": False,
        "payee_first_time": False,
        "amount_ratio": 1.0,
        "lookalike_score": 0.85
    }
    decision = policy_engine.evaluate(features)
    assert "eligibility_gate_passed" in decision.applied_rules


def test_corroboration_rule_single_signal_caps_at_amber(policy_engine: PolicyEngine):
    """A single weak Family A signal (on_call only) never warns: no amber, never red.
    (Changed: on-call alone used to give amber on every payment, which caused alert fatigue.)"""
    features = {
        "on_call": True,
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "payee_first_time": False,
        "payee_age_days": 500.0,
        "payee_verified": True,
        "payee_new_payers_24h": 1,
        "lookalike_score": 0.0,
        "amount_ratio": 1.1,
        "note_text": "regular bill"
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "green"
    assert decision.hold_minutes == 0
    assert decision.elevated_families_count == 1
    assert decision.family_flags["A"] is True
    assert decision.family_flags["B"] is False


def test_corroboration_rule_single_signal_payee_risk_caps_at_amber(policy_engine: PolicyEngine):
    """A single weak Family B signal (young first-time payee, normal amount) does not warn.
    (Changed: any single family used to give amber regardless of the score.)"""
    features = {
        "on_call": False,
        "screen_shared": False,
        "payee_first_time": True,
        "payee_age_days": 5.0,  # Young account
        "payee_verified": False,
        "payee_new_payers_24h": 1,
        "lookalike_score": 0.10,
        "amount_ratio": 1.0,
        "note_text": "groceries"
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "green"
    assert decision.hold_minutes == 0
    assert decision.elevated_families_count == 1
    assert decision.family_flags["B"] is True


def test_corroboration_rule_two_families_triggers_red(policy_engine: PolicyEngine):
    """Rule 5: Two independent families firing (Family A + Family B) triggers RED with 30m hold."""
    features = {
        "on_call": True,              # Family A (+0.45) -> Family A fires
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "payee_first_time": True,     # Family B
        "payee_age_days": 2.0,        # Family B (+0.35) -> Family B fires
        "payee_verified": False,
        "payee_new_payers_24h": 15,
        "lookalike_score": 0.85,      # Family B (+0.45)
        "amount_ratio": 1.2,
        "note_text": "kyc verification"
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "red"
    assert decision.hold_minutes == 30
    assert decision.elevated_families_count >= 2
    assert "ON_CALL" in decision.reasons
    assert "LOOKALIKE_HANDLE" in decision.reasons or "NEW_PAYEE_YOUNG_ACCOUNT" in decision.reasons


def test_corroboration_rule_three_families_triggers_red(policy_engine: PolicyEngine):
    """Rule 5: Coercion (A) + Mule payee (B) + Huge amount (D) strongly triggers RED."""
    features = {
        "on_call": True,
        "screen_shared": True,        # Family A fires heavily
        "payee_first_time": True,
        "payee_age_days": 1.0,        # Family B fires
        "lookalike_score": 0.88,
        "amount_ratio": 8.0,          # Family D fires
        "amount_z": 3.5,
        "note_text": "cbi clearance fee"
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "red"
    assert decision.hold_minutes == 30
    assert decision.elevated_families_count >= 3


def test_repeat_warnings_are_not_silenced(policy_engine: PolicyEngine):
    """There is no weekly warning cap: a single-family amber the scorer raises is always shown.
    (The cap used to turn it green; that hid the later payments of multi-step scams.)"""
    features = {
        "on_call": False,
        "screen_shared": False,
        "payee_first_time": True,
        "payee_age_days": 20.0,
        "payee_verified": False,
        "payee_new_payers_24h": 6,
        "payee_reports_prior": 1,
        "lookalike_score": 0.0,
        "amount_ratio": 1.0
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "amber"
    assert decision.elevated_families_count == 1


def test_red_always_intervenes(policy_engine: PolicyEngine):
    """RED is never downgraded."""
    features = {
        "on_call": True,
        "screen_shared": True,
        "payee_first_time": True,
        "payee_age_days": 2.0,
        "lookalike_score": 0.85,
        "amount_ratio": 5.0
    }
    decision = policy_engine.evaluate(features)
    assert decision.tier == "red"
    assert decision.hold_minutes == 30


def test_questionnaire_cannot_lower_red_tier(policy_engine: PolicyEngine):
    """Rule 7: Questionnaire answers cannot lower an existing RED decision."""
    features = {
        "on_call": True,
        "payee_first_time": True,
        "payee_age_days": 1.0,
        "lookalike_score": 0.80,
        "amount_ratio": 6.0
    }
    # User claims nothing is wrong (scammer coaching them to say so)
    denial_answers = {
        "is_anyone_guiding_you": False,
        "caller_claimed_police": False
    }
    decision = policy_engine.evaluate(features, questionnaire_answers=denial_answers)
    assert decision.tier == "red"
    assert decision.hold_minutes == 30
    assert "questionnaire_denial_retained_red" in decision.applied_rules


def test_questionnaire_can_raise_risk_to_red(policy_engine: PolicyEngine):
    """Rule 7: Questionnaire answers admitting coercion escalate AMBER to RED."""
    features = {
        # Only single family initially -> would normally be amber
        "on_call": True,
        "payee_first_time": False,
        "amount_ratio": 1.0,
        "lookalike_score": 0.0
    }
    coerced_answers = {
        "caller_claimed_police": True,
        "asked_to_install_app": True
    }
    decision = policy_engine.evaluate(features, questionnaire_answers=coerced_answers)
    assert decision.tier == "red"
    assert decision.hold_minutes == 30
    assert "questionnaire_escalated_to_red" in decision.applied_rules
    assert "REMOTE_APP_NEW" in decision.reasons


def test_fail_open_on_timeout(policy_engine: PolicyEngine):
    """Rule 8: Scoring timeout (>300ms) fails open with device-only check and logs event."""
    features = {
        "screen_shared": False,
        "remote_app_new": False,
        "on_call": False,
        "payee_first_time": True,
        "amount_ratio": 3.0
    }
    decision = policy_engine.evaluate(features, simulate_timeout=True)
    assert decision.tier == "green"
    assert "fail_open_device_check" in decision.applied_rules
    assert "scoring_simulated_timeout" in decision.applied_rules


def test_fail_open_on_exception(policy_engine: PolicyEngine):
    """Rule 8: Scorer exception fails open gracefully with device-only check."""
    features = {
        "screen_shared": True,  # Critical device signal
        "remote_app_new": False,
        "on_call": False,
        "payee_first_time": True,
        "amount_ratio": 1.0
    }
    decision = policy_engine.evaluate(features, simulate_failure=True)
    # Fail-open catches screen sharing and assigns amber caution
    assert decision.tier == "amber"
    assert "SCREEN_SHARED" in decision.reasons
    assert "fail_open_device_check" in decision.applied_rules


def test_hold_minutes_per_tier(policy_engine: PolicyEngine):
    """Hold minutes invariant: 30 minutes for RED, 0 for all other tiers."""
    red_feats = {
        "on_call": True,
        "payee_first_time": True,
        "payee_age_days": 2.0,
        "lookalike_score": 0.85,
        "amount_ratio": 5.0
    }
    amber_feats = {
        "on_call": True, "payee_first_time": False, "amount_ratio": 1.0, "lookalike_score": 0.0
    }
    green_feats = {
        "on_call": False, "payee_first_time": False, "amount_ratio": 1.0, "lookalike_score": 0.0
    }

    assert policy_engine.evaluate(red_feats).hold_minutes == 30
    assert policy_engine.evaluate(amber_feats).hold_minutes == 0
    assert policy_engine.evaluate(green_feats).hold_minutes == 0
    assert policy_engine.evaluate(green_feats, is_confirmed_scam_payee=True).hold_minutes == 0
