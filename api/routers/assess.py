"""
Risk Assessment Endpoint: POST /v1/risk/assess
Enforces the strict contract from README Section 17.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException

from api.models import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    QuestionnaireRequest,
    AppealRequest,
    AppealResponse,
    PaymentCompleteRequest,
    PaymentCompleteResponse,
)
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.policy.engine import PolicyEngine, apply_questionnaire
from api.policy.intent import resolve_note_intent
from api.policy.templates import resolve_template_id
from api.policy.scorer import get_satark_scorer
from api.config import DB_PATH, POLICY_FILE_PATH
from api.intel.domain_intel import lookup_domain

router = APIRouter(prefix="/v1", tags=["risk"])

# Singleton instances for request execution
_feature_store = SQLiteFeatureStore(DB_PATH)
_audit_store = AuditLogStore(DB_PATH)
_policy_engine = PolicyEngine(POLICY_FILE_PATH, scorer=get_satark_scorer())


def get_feature_store() -> SQLiteFeatureStore:
    return _feature_store


def get_audit_store() -> AuditLogStore:
    return _audit_store


def get_policy_engine() -> PolicyEngine:
    return _policy_engine


# Entry channels the model was trained on (ml/train.py ENTRY).
MODEL_ENTRY_CHANNELS = {"contact", "deep_link_sms", "deep_link_whatsapp", "merchant_collect", "qr_gallery", "qr_scan",
                        "typed_vpa"}

REQUIRED_NON_LINK_FEATURES = [
    "on_call", "caller_in_contacts", "screen_shared", "remote_app_present", "remote_app_new", "app_switches",
    "typing_z", "pause_z", "pin_time_z", "device_new", "failed_auth",
    "payee_first_time", "payee_age_days", "payee_verified", "payee_new_payers_24h", "payee_reports_prior", "lookalike_score",
    "amount", "amount_ratio", "amount_z", "amount_vs_max", "hour", "hour_familiarity",
    "same_payee_count_24h", "same_payee_sum_24h", "escalation_ratio", "baseline_ready"
]


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


@router.post("/risk/assess", response_model=RiskAssessmentResponse)
def assess_risk(
    req: RiskAssessmentRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store),
    policy: PolicyEngine = Depends(get_policy_engine)
) -> RiskAssessmentResponse:
    """
    Evaluates real-time risk for payment transaction using Satark fusion model.
    Returns STRICTLY: {tier, reasons[], template_id, hold_minutes, case_id}.
    Score and model weights are never returned to the app.
    """
    case_id = f"c-{uuid.uuid4().hex[:8]}"
    user_id = req.user_ref or "default_user"
    payee_vpa = req.payee_vpa.strip().lower()

    # 1. Compute User Baseline Features point-in-time from store
    baseline = store.compute_baseline_features(
        user_id=user_id,
        payee_vpa=payee_vpa,
        amount=req.amount
    )

    # 2. Compute Timing Dynamics Z-scores from user's last 50 sessions.
    # PIN time is unknown here: this check runs BEFORE the PIN screen, so any client value is ignored.
    timing_z = store.compute_timing_z_scores(
        user_id=user_id,
        typing_ms=req.session.typing_ms,
        pauses=req.session.pauses,
        pin_secs=None
    )

    # 3. Retrieve Payee Risk Profile from registry (fan-in excludes this payer)
    payee_profile = store.get_payee_profile(payee_vpa, exclude_payer=user_id)

    # 4. Check historical relationship with payee
    trusted_history = store.get_trusted_payee_history(user_id, payee_vpa)

    # 6. Note intent only; raw note text is never stored or scored
    note_intent = resolve_note_intent(req.context.note_intent, req.context.note_text)

    # 7. Resolve link intelligence: only when entry_channel is a link type
    entry_channel = (req.entry_channel or "typed_vpa").lower()
    is_link_entry = entry_channel in (
        "deep_link_sms", "deep_link_whatsapp", "qr from a link", "qr_from_link", "link"
    ) or bool(req.context.link_domain)
    if entry_channel not in MODEL_ENTRY_CHANNELS:
        # The model only knows these channels; an unknown one would zero every entry input. A payee
        # entered some other way is treated as typed by hand.
        entry_channel = "typed_vpa"

    if is_link_entry:
        intel = lookup_domain(req.context.link_domain)
        link_bad = intel["bad"] if intel["bad"] is not None else (
            1 if req.context.link_bad is True else (0 if req.context.link_bad is False else None)
        )
        link_domain_age_days = _safe_float(intel["age_days"]) if intel["age_days"] is not None else _safe_float(req.context.link_domain_age_days)
        secs_link_to_pay = _safe_float(req.context.secs_link_to_pay)
    else:
        # For non-link entry channels, pass None so the scorer treats them as unknown
        link_bad = None
        link_domain_age_days = None
        secs_link_to_pay = None

    # 8. Assemble complete point-in-time feature dictionary matching model feature names
    feature_vector: Dict[str, Any] = {
        # Session Coercion
        "on_call": bool(req.session.on_call),
        # Only a call with a saved contact counts; not measured (None) is treated as an unknown caller.
        "caller_in_contacts": bool(req.session.on_call and req.session.caller_in_contacts is True),
        "screen_shared": bool(req.session.screen_shared),
        "remote_app_present": bool(req.session.remote_app_present),
        "remote_app_new": bool(req.session.remote_app_new),
        "app_switches": _safe_int(req.session.app_switches),
        "typing_z": _safe_float(timing_z.get("typing_z")),
        "pause_z": _safe_float(timing_z.get("pause_z")),
        "pin_time_z": _safe_float(timing_z.get("pin_time_z")),
        "device_new": bool(req.session.device_new),
        "failed_auth": _safe_int(req.session.failed_auth),

        # Payee Risk
        "payee_first_time": bool(baseline.get("payee_first_time")),
        "payee_age_days": _safe_float(payee_profile.get("payee_age_days")),
        "payee_verified": bool(payee_profile.get("payee_verified")),
        "payee_new_payers_24h": _safe_int(payee_profile.get("payee_new_payers_24h")),
        "payee_reports_prior": _safe_int(payee_profile.get("payee_reports_prior")),
        "lookalike_score": _safe_float(payee_profile.get("lookalike_score")),

        # Context & Link
        "entry_channel": entry_channel,
        "link_bad": link_bad,
        "link_domain_age_days": link_domain_age_days,
        "secs_link_to_pay": secs_link_to_pay,
        "note_intent": note_intent,

        # Personal Baseline
        "amount": _safe_float(baseline.get("amount")),
        "amount_ratio": _safe_float(baseline.get("amount_ratio")),
        "amount_z": _safe_float(baseline.get("amount_z")),
        "amount_vs_max": _safe_float(baseline.get("amount_vs_max")),
        "hour": _safe_int(baseline.get("hour")),
        "hour_familiarity": _safe_float(baseline.get("hour_familiarity")),
        "same_payee_count_24h": _safe_int(baseline.get("same_payee_count_24h")),
        "same_payee_sum_24h": _safe_float(baseline.get("same_payee_sum_24h")),
        "escalation_ratio": _safe_float(baseline.get("escalation_ratio")),
        "baseline_ready": bool(baseline.get("baseline_ready"))
    }

    # Validate that no required feature is missing
    missing_features = [k for k in REQUIRED_NON_LINK_FEATURES if feature_vector.get(k) is None]
    if missing_features:
        # Safe fallback tier (amber, CHECK_UNAVAILABLE) on missing features, never green
        fallback_reasons = ["CHECK_UNAVAILABLE"]
        template_id = "amber_caution_v1"
        audit_entry = audit.append_log(
            case_id=case_id,
            user_id=user_id,
            payee_vpa=payee_vpa,
            tier="amber",
            reasons=fallback_reasons
        )
        store.record_case(
            case_id=case_id,
            txn_ref=req.txn_ref,
            user_id=user_id,
            payee_vpa=payee_vpa,
            amount=req.amount,
            tier="amber",
            reasons=fallback_reasons,
            template_id=template_id,
            hold_minutes=0,
            feature_vector=feature_vector,
            evidence_pack={
                "features": feature_vector,
                "error": f"Missing features: {missing_features}",
                "audit": audit_entry
            }
        )
        return RiskAssessmentResponse(
            tier="amber",
            reasons=fallback_reasons,
            template_id=template_id,
            hold_minutes=0,
            case_id=case_id
        )

    # 8. Evaluate Policy Engine with Satark fusion model scoring
    try:
        decision = policy.evaluate(
            features=feature_vector,
            is_confirmed_scam_payee=payee_profile["is_confirmed_scam"],
            trusted_payee_history=trusted_history,
            questionnaire_answers=req.questionnaire_answers,
            pair_trust=store.get_pair_trust(user_id, payee_vpa, payee_profile["payee_reports_prior"])
        )
    except Exception as exc:
        # Safe fallback tier (amber, reason code CHECK_UNAVAILABLE), log to audit, never green
        fallback_reasons = ["CHECK_UNAVAILABLE"]
        template_id = "amber_caution_v1"
        audit_entry = audit.append_log(
            case_id=case_id,
            user_id=user_id,
            payee_vpa=payee_vpa,
            tier="amber",
            reasons=fallback_reasons
        )
        store.record_case(
            case_id=case_id,
            txn_ref=req.txn_ref,
            user_id=user_id,
            payee_vpa=payee_vpa,
            amount=req.amount,
            tier="amber",
            reasons=fallback_reasons,
            template_id=template_id,
            hold_minutes=0,
            feature_vector=feature_vector,
            evidence_pack={
                "features": feature_vector,
                "error": str(exc),
                "audit": audit_entry
            }
        )
        return RiskAssessmentResponse(
            tier="amber",
            reasons=fallback_reasons,
            template_id=template_id,
            hold_minutes=0,
            case_id=case_id
        )

    # Strict rule: Only include reasons when tier is amber or red (or decline)
    response_reasons = decision.reasons if decision.tier in ("amber", "red", "decline") else []

    # 9. Cryptographic hash-chained audit logging
    audit_entry = audit.append_log(
        case_id=case_id,
        user_id=user_id,
        payee_vpa=payee_vpa,
        tier=decision.tier,
        reasons=response_reasons
    )

    # 10. Store Case & Evidence Pack for security analysts
    evidence_pack = {
        "features": feature_vector,
        "score": decision.score,
        "family_flags": decision.family_flags,
        "family_contrib": decision.raw_score_result.family_contrib if decision.raw_score_result else {},
        "applied_rules": decision.applied_rules,
        "audit": audit_entry,
        "payee_age_known": payee_profile.get("payee_age_known", False),
        "questionnaire_answers": req.questionnaire_answers
    }

    store.record_case(
        case_id=case_id,
        txn_ref=req.txn_ref,
        user_id=user_id,
        payee_vpa=payee_vpa,
        amount=req.amount,
        tier=decision.tier,
        reasons=response_reasons,
        template_id=decision.template_id,
        hold_minutes=decision.hold_minutes,
        feature_vector=feature_vector,
        evidence_pack=evidence_pack
    )

    # NOTE: nothing is recorded as a payment here. A risk check is not a payment: the user may
    # cancel, or the payment may be declined. The app calls POST /v1/payments/complete after the PIN.

    # 11. STRICT RESPONSE: NEVER return score or weights to app
    return RiskAssessmentResponse(
        tier=decision.tier,
        reasons=response_reasons,
        template_id=decision.template_id,
        hold_minutes=decision.hold_minutes,
        case_id=case_id
    )


def _load_case_for_user(store: SQLiteFeatureStore, case_id: str, user_ref: str) -> Dict[str, Any]:
    row = store.get_case(case_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    if row["user_id"] != (user_ref or "").strip().lower():
        raise HTTPException(status_code=403, detail="Case belongs to a different user")
    return row


@router.post("/risk/{case_id}/questionnaire", response_model=RiskAssessmentResponse)
def submit_questionnaire(
    case_id: str,
    req: QuestionnaireRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store),
    policy: PolicyEngine = Depends(get_policy_engine)
) -> RiskAssessmentResponse:
    """
    Attaches red-tier questionnaire answers to an EXISTING case. Answers can only raise the
    tier (e.g. "someone is guiding me" turns amber into red); they never lower it.
    """
    row = _load_case_for_user(store, case_id, req.user_ref)
    tier = row["tier"]
    reasons = json.loads(row["reasons"] or "[]")
    hold = int(row["hold_minutes"])
    if tier == "decline":
        return RiskAssessmentResponse(tier=tier, reasons=reasons, template_id=row["template_id"],
                                      hold_minutes=hold, case_id=case_id)

    rules: List[str] = []
    new_tier, new_reasons, new_hold = apply_questionnaire(tier, reasons, hold, req.answers, policy.config, rules)
    template_id = row["template_id"]
    if (new_tier, new_reasons) != (tier, reasons):
        template_id = resolve_template_id(new_tier, new_reasons, config_path=policy.template_map_path)
        audit.append_log(case_id=case_id, user_id=row["user_id"], payee_vpa=row["payee_vpa"],
                         tier=new_tier, reasons=new_reasons)
    store.update_case_decision(case_id, new_tier, new_reasons, template_id, new_hold,
                               {"questionnaire_answers": req.answers, "questionnaire_rules": rules})
    return RiskAssessmentResponse(tier=new_tier, reasons=new_reasons, template_id=template_id,
                                  hold_minutes=new_hold, case_id=case_id)


@router.post("/risk/{case_id}/appeal", response_model=AppealResponse)
def appeal_case(
    case_id: str,
    req: AppealRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store)
) -> AppealResponse:
    """
    "This was me" on an amber warning: the case is marked disputed and later amber checks for this
    user and payee turn green. Red and decline have no instant appeal, because a coaching scammer
    would simply say "tap This was me": use /false-alarm, which changes nothing until an analyst
    accepts it.
    """
    row = _load_case_for_user(store, case_id, req.user_ref)
    if row["tier"] != "amber":
        raise HTTPException(status_code=409, detail="Only an amber warning can be marked 'This was me'")
    features = json.loads(row["feature_vector"] or "{}")
    if "CHECK_UNAVAILABLE" in json.loads(row["reasons"] or "[]"):
        raise HTTPException(status_code=409, detail="This check did not run, so there is nothing to vouch for")
    if any(features.get(k) for k in ("on_call", "screen_shared", "remote_app_present", "remote_app_new")):
        # A scammer on the line or controlling the screen could have coached this tap.
        raise HTTPException(status_code=409, detail="Not available while a call or remote session was active")
    store.trust_pair(row["user_id"], row["payee_vpa"], "user", case_id, features.get("payee_reports_prior") or 0)
    store.update_case_decision(case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
                               int(row["hold_minutes"]), {"dispute": "this_was_me"})
    audit.append_log(case_id=case_id, user_id=row["user_id"], payee_vpa=row["payee_vpa"],
                     tier="user_this_was_me", reasons=["USER_VOUCHED_PAYEE"])
    return AppealResponse(case_id=case_id, status="payee_trusted")


@router.post("/risk/{case_id}/false-alarm", response_model=AppealResponse)
def report_false_alarm(
    case_id: str,
    req: AppealRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store)
) -> AppealResponse:
    """Red or decline: sends the case to the analyst console. Nothing else changes."""
    row = _load_case_for_user(store, case_id, req.user_ref)
    if row["tier"] not in ("red", "decline"):
        raise HTTPException(status_code=409, detail="Only a red pause or a decline can be reported as a false alarm")
    store.update_case_decision(case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
                               int(row["hold_minutes"]), {"dispute": "false_alarm_pending"})
    audit.append_log(case_id=case_id, user_id=row["user_id"], payee_vpa=row["payee_vpa"],
                     tier="user_false_alarm_report", reasons=["USER_DISPUTED"])
    return AppealResponse(case_id=case_id, status="sent_for_review")


@router.post("/payments/complete", response_model=PaymentCompleteResponse)
def complete_payment(
    req: PaymentCompleteRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> PaymentCompleteResponse:
    """
    Called by the app after the PIN succeeds. Only completed payments update the user's
    baseline, the payee's first-time status and fan-in. Declined payments and payments
    still inside their red-tier hold are refused (server-side, not just in the app).
    """
    row = _load_case_for_user(store, req.case_id, req.user_ref)
    if row["payee_vpa"] != req.payee_vpa.strip().lower() or abs(float(row["amount"]) - float(req.amount)) > 0.01:
        raise HTTPException(status_code=409, detail="Payee or amount does not match the risk check")
    if row["tier"] == "decline":
        raise HTTPException(status_code=403, detail="Declined payments cannot be completed")
    if row["tier"] == "red":
        created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < created + timedelta(minutes=int(row["hold_minutes"])):
            raise HTTPException(status_code=409, detail="Safety hold is still active")

    evidence = json.loads(row["evidence_pack"] or "{}")
    if evidence.get("completed"):
        return PaymentCompleteResponse(status="already_recorded", case_id=req.case_id)
    if evidence.get("cancelled"):
        raise HTTPException(status_code=409, detail="This payment was cancelled when it was reported as a scam")

    user_id = row["user_id"]
    store.record_payment(payer_id=user_id, payee_vpa=row["payee_vpa"], amount=float(row["amount"]))
    store.record_session(user_id, req.typing_ms, req.pauses, req.pin_secs)
    store.update_case_decision(
        req.case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
        int(row["hold_minutes"]),
        {"completed": True, "completed_at": datetime.now(timezone.utc).isoformat()}
    )
    return PaymentCompleteResponse(status="recorded", case_id=req.case_id)
