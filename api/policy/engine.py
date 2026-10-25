"""
Pure Python Policy Engine for SATARK scam-interruption layer.
Strictly NO FastAPI imports, 100% unit-testable.
"""

import math
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from api.policy.scorer import BaseScorer, StubScorer, ScoreResult, get_satark_scorer
from api.model_client import ModelServiceError, ModelValidationError
from api.policy.templates import resolve_template_id
from api.policy.intent import resolve_note_intent, SUSPICIOUS_INTENTS
from api.config import TEMPLATE_MAP_PATH, POLICY_FILE_PATH


def strong_coercion(features: Dict[str, Any]) -> bool:
    """Signals strong enough to warn on their own: someone is watching or controlling the screen."""
    return bool(features.get("screen_shared") or features.get("remote_app_new"))


def verified_unreported(features: Dict[str, Any]) -> bool:
    """A verified merchant that nobody has reported. Once reported, the verified badge no longer exempts
    it from the fan-in, stranger and collect checks (a verified account can turn out to be a mule)."""
    return bool(features.get("payee_verified")) and not (features.get("payee_reports_prior") or 0) > 0


def reported_or_bad_link(features: Dict[str, Any]) -> bool:
    """The payee has been reported or the payment came from a known-bad link: a shortcut that skips
    the model (trusted payee, eligibility gate) must not apply."""
    return bool((features.get("payee_reports_prior") or 0) > 0 or features.get("link_bad") == 1)


def apply_questionnaire(
    tier: str,
    reasons: List[str],
    hold_minutes: int,
    answers: Optional[Dict[str, Any]],
    config: Dict[str, Any],
    applied_rules: List[str],
) -> Tuple[str, List[str], int]:
    """
    Red-tier questionnaire. Answers can only RAISE risk; they never lower a tier,
    and the hold always runs on red. Shared by /v1/risk/assess and the
    questionnaire endpoint so both behave identically.
    """
    if not answers:
        return tier, reasons, hold_minutes
    applied_rules.append("questionnaire_evaluated")
    reasons = list(reasons)
    claims_police = answers.get("caller_claimed_police", False)
    claims_refund = answers.get("caller_promised_refund", False)
    installed_app = answers.get("asked_to_install_app", False)
    being_guided = answers.get("is_anyone_guiding_you") is True

    if claims_police or claims_refund or installed_app or being_guided:
        if tier not in ("red", "decline"):
            tier = "red"
            hold_minutes = int(config.get("hold_minutes", 30))
            applied_rules.append("questionnaire_escalated_to_red")
        if claims_police and "ON_CALL" not in reasons:
            reasons.append("ON_CALL")
        if being_guided and "USER_REPORTED_GUIDANCE" not in reasons:
            reasons.append("USER_REPORTED_GUIDANCE")
        if installed_app and "REMOTE_APP_NEW" not in reasons:
            reasons.append("REMOTE_APP_NEW")

    if tier == "red" and answers.get("is_anyone_guiding_you") is False:
        applied_rules.append("questionnaire_denial_retained_red")
    return tier, reasons, hold_minutes


@dataclass
class PolicyDecision:
    """Internal decision structure from policy engine."""
    tier: str
    reasons: List[str]
    template_id: str
    hold_minutes: int
    score: float
    elevated_families_count: int
    family_flags: Dict[str, bool] = field(default_factory=dict)
    applied_rules: List[str] = field(default_factory=list)
    raw_score_result: Optional[ScoreResult] = None


class PolicyEngine:
    """
    Evaluates risk features and applies the exact decision order from README Section 7.
    """

    def __init__(
        self,
        policy_config_path: Optional[str] = None,
        scorer: Optional[Any] = None,
        custom_config: Optional[Dict[str, Any]] = None,
        template_map_path: Optional[str] = None
    ):
        self.policy_config_path = policy_config_path
        self.template_map_path = template_map_path or TEMPLATE_MAP_PATH
        self.fallback_scorer = StubScorer()
        try:
            self.scorer = scorer or get_satark_scorer()
        except Exception:
            self.scorer = self.fallback_scorer
        self.config: Dict[str, Any] = {}

        if custom_config:
            self.config = custom_config
        elif policy_config_path and Path(policy_config_path).exists():
            self.reload_policy()
        else:
            self.config = self._default_config()

    @staticmethod
    def compute_family_contributions(features: Dict[str, Any]) -> Dict[str, float]:
        """Calculates family contributions from features for 2-of-4 corroboration."""
        fam_a = 0.0
        if features.get("on_call", False):
            # A call with a saved contact (family, a known shop) is weak evidence on its own.
            fam_a += 0.15 if features.get("caller_in_contacts") else 0.45
        if features.get("screen_shared", False):
            fam_a += 0.50
        remote_present = features.get("remote_app_present", False)
        remote_new = features.get("remote_app_new", False)
        if remote_present or remote_new:
            fam_a += 0.55 if remote_new else 0.35
        try:
            typing_z = float(features.get("typing_z", 0.0))
            pause_z = float(features.get("pause_z", 0.0))
            if typing_z >= 1.5 or pause_z >= 2.0:
                fam_a += 0.25
        except (ValueError, TypeError):
            pass
        try:
            pin_time_z = float(features.get("pin_time_z", 0.0))
            if pin_time_z >= 2.0:
                fam_a += 0.20
        except (ValueError, TypeError):
            pass

        fam_b = 0.0
        first_time = features.get("payee_first_time", False)
        try:
            payee_age = float(features.get("payee_age_days", 365.0))
        except (ValueError, TypeError):
            payee_age = 365.0
        if first_time:
            fam_b += 0.20
            if payee_age <= 30.0:
                fam_b += 0.35
        try:
            new_payers = int(features.get("payee_new_payers_24h", 0))
        except (ValueError, TypeError):
            new_payers = 0
        if new_payers >= 5 and not verified_unreported(features):
            fam_b += 0.40
        try:
            reports = int(features.get("payee_reports_prior", 0))
        except (ValueError, TypeError):
            reports = 0
        if reports >= 1:
            fam_b += 0.50
        try:
            lookalike = float(features.get("lookalike_score", 0.0))
        except (ValueError, TypeError):
            lookalike = 0.0
        if lookalike >= 0.70:
            fam_b += 0.45

        fam_c = 0.0
        if features.get("link_bad") is True:
            fam_c += 0.55
        domain_age = features.get("link_domain_age_days")
        if domain_age is not None:
            try:
                if 0 <= float(domain_age) < 15.0:
                    fam_c += 0.30
            except (ValueError, TypeError):
                pass
        # Only the note's intent label is used; raw note text never reaches scoring.
        if str(features.get("note_intent") or "").lower() in SUSPICIOUS_INTENTS:
            fam_c += 0.30

        fam_d = 0.0
        try:
            amount_ratio = float(features.get("amount_ratio", 1.0))
            amount_z = float(features.get("amount_z", 0.0))
            if amount_ratio >= 4.0 or amount_z >= 2.5:
                fam_d += 0.45
            elif amount_ratio >= 2.5:
                fam_d += 0.25
        except (ValueError, TypeError):
            pass
        try:
            escalation = float(features.get("escalation_ratio", 1.0))
            same_payee_count = int(features.get("same_payee_count_24h", 0))
            if escalation >= 2.0 and same_payee_count >= 1:
                fam_d += 0.40
        except (ValueError, TypeError):
            pass

        return {
            "A": round(fam_a, 3),
            "B": round(fam_b, 3),
            "C": round(fam_c, 3),
            "D": round(fam_d, 3)
        }

    def _large_first_payment_to_stranger(self, features: Dict[str, Any],
                                         payee_history: Optional[Tuple[int, int]] = None) -> bool:
        """A payment of at least the configured amount (counting what was sent to them in the last 24
        hours) to someone who is not yet an established payee, a saved contact or a verified merchant.
        Not just the first payment: a "Rs 1 to verify" or a split into smaller payments would otherwise
        switch the check off. Picking the payee from contacts does not count while a caller who is not
        a saved contact is on the line, or when the handle looks like a brand ("save my number as SBI
        Officer, then pay from contacts")."""
        floor = float(self.config.get("stranger_amount_floor", 25000))
        try:
            amount = float(features.get("amount") or 0) + float(features.get("same_payee_sum_24h") or 0)
        except (TypeError, ValueError):
            return False
        known = self.config.get("trusted_payee", {})
        paid_before, paid_over_days = payee_history or (0, 0)
        established = paid_before >= known.get("min_payments", 3) and \
            paid_over_days >= known.get("min_history_days", 30)
        unknown_caller = bool(features.get("on_call")) and not features.get("caller_in_contacts")
        brand_like = float(features.get("lookalike_score") or 0) >= \
            float(self.config.get("eligibility_gate", {}).get("bypass_on_lookalike", 0.70))
        from_contacts = features.get("entry_channel") == "contact" and not unknown_caller and not brand_like
        return (bool(features.get("payee_first_time")) or not established) and not from_contacts \
            and not verified_unreported(features) and amount >= floor

    def _suspicious_collect(self, features: Dict[str, Any]) -> bool:
        if features.get("entry_channel") != "merchant_collect" or verified_unreported(features):
            return False
        return not self.config.get("collect_amber", {}).get("needs_receive_note", True) \
            or features.get("note_intent") in ("receive", "refund")

    def _unknown_caller_new_payee(self, features: Dict[str, Any], score: float) -> bool:
        cfg = self.config.get("unknown_caller_amber", {})
        unknown_caller = bool(features.get("on_call")) and not features.get("caller_in_contacts")
        return unknown_caller and bool(features.get("payee_first_time")) \
            and float(features.get("amount_ratio") or 0) >= cfg.get("min_amount_ratio", 4.0) \
            and score >= cfg.get("min_score", 0.7)

    def _default_config(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "amber_threshold": 0.35,
            "red_threshold": 0.50,
            "hold_minutes": 30,
            "family_thresholds": {
                "A": 0.40,
                "B": 0.40,
                "C": 0.35,
                "D": 0.35
            },
            "trusted_payee": {
                "min_payments": 3,
                "min_history_days": 30
            },
            "eligibility_gate": {
                "min_amount_ratio": 2.0,
                "force_first_time": True,
                "bypass_on_family_a": True,
                "bypass_on_lookalike": 0.70
            },
            "stranger_amount_floor": 25000,
            "timeout_ms": 300,
            "fail_open_on_error": True
        }

    def reload_policy(self) -> None:
        """Hot-reloads the policy rules from YAML."""
        if not self.policy_config_path:
            return
        path = Path(self.policy_config_path)
        if path.exists():
            try:
                import yaml  # Optional C-extension; lazy import avoids build failures
                with open(path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        self.config = loaded
            except ImportError:
                # yaml not available (e.g. Python 3.15 without MSVC build tools);
                # fall back to the built-in JSON-based default config silently.
                pass

    def evaluate(
        self,
        features: Dict[str, Any],
        is_confirmed_scam_payee: bool = False,
        trusted_payee_history: Optional[Tuple[int, int]] = None,  # (payment_count, history_days)
        questionnaire_answers: Optional[Dict[str, Any]] = None,
        pair_trust: Optional[str] = None,  # "user" ("This was me" on an amber) or "analyst" (appeal accepted)
        vouched_amount: Optional[float] = None,  # amount of the case the user vouched for
        simulate_timeout: bool = False,
        simulate_failure: bool = False
    ) -> PolicyDecision:
        """
        Executes the decision flow in strict order:
        1. Analyst-confirmed scam payee -> DECLINE
        2. Trusted payee rule -> GREEN silently unless Family A fires, the payee was reported, the link
           is known bad, or the amount jumps 3x over the last payment to them
        3. Eligibility gate -> score only first-time, unusual amount, reported payee, bad link or
           scam-story note; else GREEN silently
        4. Scorer invocation (a late score is still used; on error or a non-finite score, fail open
           with the checks that need no model)
        5. Tier: RED needs score >= red_threshold and >=2 families; AMBER needs score >= amber
           threshold, screen sharing / a new remote-access app, or a large first payment to a stranger
        6. Vouched-for payee can lower later warnings (never during a call or remote session)
        7. Red-tier questionnaire: can only raise risk, never lower RED tier
        """
        applied_rules: List[str] = []

        # Work on a copy: derive the note intent and drop raw note text so it never
        # reaches the scorer, the evidence pack or the logs.
        features = dict(features)
        note_text = features.pop("note_text", None)
        features["note_intent"] = resolve_note_intent(features.get("note_intent"), note_text)

        # ---------------------------------------------------------------------
        # Step 1: Analyst-confirmed scam payee -> DECLINE
        # ---------------------------------------------------------------------
        if is_confirmed_scam_payee:
            applied_rules.append("analyst_confirmed_decline")
            reasons = ["ANALYST_CONFIRMED_SCAM"]
            return PolicyDecision(
                tier="decline",
                reasons=reasons,
                template_id=resolve_template_id("decline", reasons, config_path=self.template_map_path),
                hold_minutes=0,
                score=1.0,
                elevated_families_count=4,
                family_flags={"A": True, "B": True, "C": True, "D": True},
                applied_rules=applied_rules
            )

        # ---------------------------------------------------------------------
        # Step 2: Trusted-payee rule (3+ payments over 30+ days)
        # ---------------------------------------------------------------------
        has_family_a = bool(
            features.get("on_call", False) or
            features.get("screen_shared", False) or
            features.get("remote_app_present", False) or
            features.get("remote_app_new", False)
        )

        if trusted_payee_history:
            tx_count, history_days = trusted_payee_history
            min_tx = self.config.get("trusted_payee", {}).get("min_payments", 3)
            min_days = self.config.get("trusted_payee", {}).get("min_history_days", 30)

            if tx_count >= min_tx and history_days >= min_days:
                # Trust earned on small payments does not cover a payee reported since, a known-bad
                # link, or a sudden jump (3x or more over the last payment to them): account takeover
                # of a regular payee, or a task scam that built history first.
                big_step = float(features.get("escalation_ratio") or 1.0) >= 3
                if has_family_a:
                    applied_rules.append("trusted_payee_bypassed_by_family_a")
                elif reported_or_bad_link(features) or big_step:
                    applied_rules.append("trusted_payee_bypassed_by_risk")
                else:
                    applied_rules.append("trusted_payee_silent_pass")
                    return PolicyDecision(
                        tier="green",
                        reasons=[],
                        template_id=resolve_template_id("green", [], is_silent_pass=True, config_path=self.template_map_path),
                        hold_minutes=0,
                        score=0.02,
                        elevated_families_count=0,
                        family_flags={"A": False, "B": False, "C": False, "D": False},
                        applied_rules=applied_rules
                    )

        # ---------------------------------------------------------------------
        # Step 3: Eligibility gate
        # ---------------------------------------------------------------------
        payee_first_time = features.get("payee_first_time", False)
        amount_ratio = float(features.get("amount_ratio", 1.0))
        lookalike = float(features.get("lookalike_score", 0.0))

        gate_cfg = self.config.get("eligibility_gate", {})
        min_amount_ratio = float(gate_cfg.get("min_amount_ratio", 2.0))
        lookalike_bypass = float(gate_cfg.get("bypass_on_lookalike", 0.70))

        is_eligible = (
            payee_first_time or
            (amount_ratio >= min_amount_ratio) or
            (has_family_a and gate_cfg.get("bypass_on_family_a", True)) or
            (lookalike >= lookalike_bypass) or
            # A reported payee, a known-bad link or a scam-story note always reaches the model.
            reported_or_bad_link(features) or
            features.get("note_intent") in SUSPICIOUS_INTENTS or
            # Split or follow-up payments that the stranger floor covers (amount_ratio can be low once
            # the scam payments themselves have become the user's baseline).
            self._large_first_payment_to_stranger(features, trusted_payee_history)
        )

        if not is_eligible:
            applied_rules.append("eligibility_gate_silent_pass")
            return PolicyDecision(
                tier="green",
                reasons=[],
                template_id=resolve_template_id("green", [], is_silent_pass=True, config_path=self.template_map_path),
                hold_minutes=0,
                score=0.05,
                elevated_families_count=0,
                family_flags={"A": False, "B": False, "C": False, "D": False},
                applied_rules=applied_rules
            )

        applied_rules.append("eligibility_gate_passed")

        # ---------------------------------------------------------------------
        # Step 4: Scorer execution with timeout (300ms) & fail-open check
        # ---------------------------------------------------------------------
        timeout_limit_ms = self.config.get("timeout_ms", 300)
        start_time = time.perf_counter()

        score_res: Optional[ScoreResult] = None
        fusion_score_val: Optional[float] = None
        model_reasons: List[str] = []
        tier_hint: Optional[str] = None
        has_error_or_timeout = False

        if simulate_timeout:
            has_error_or_timeout = True
            applied_rules.append("scoring_simulated_timeout")
        elif simulate_failure:
            has_error_or_timeout = True
            applied_rules.append("scoring_simulated_failure")
        else:
            try:
                note_intent = features.get("note_intent") or "none"
                try:
                    raw_out = self.scorer.score(features, note_intent=note_intent)
                except TypeError:
                    raw_out = self.scorer.score(features)
                except (ValueError, ModelValidationError) as val_err:
                    if "Missing features" in str(val_err) and self.fallback_scorer:
                        raw_out = self.fallback_scorer.score(features)
                    else:
                        raise ModelServiceError(str(val_err))

                # A score that arrived late is still used: the time is already spent, and dropping it
                # would turn a red mule into a fail-open green. Logged so slow scoring shows up.
                if (time.perf_counter() - start_time) * 1000.0 > timeout_limit_ms:
                    applied_rules.append("scoring_slow")
                if isinstance(raw_out, dict):
                    fusion_score_val = float(raw_out["fusion_score"])
                    model_reasons = list(raw_out.get("reasons", []))
                    tier_hint = raw_out.get("tier_hint")
                elif isinstance(raw_out, ScoreResult):
                    fusion_score_val = raw_out.score
                    model_reasons = list(raw_out.top_reasons)
                    score_res = raw_out
                if fusion_score_val is None or not math.isfinite(fusion_score_val):
                    raise ValueError(f"unusable score {fusion_score_val!r}")
            except ModelServiceError as mse:
                # Model service down / timeout / 422 error -> Safe fallback tier amber with CHECK_UNAVAILABLE
                reasons = ["CHECK_UNAVAILABLE"]
                applied_rules.append("model_service_fallback_amber")
                return PolicyDecision(
                    tier="amber",
                    reasons=reasons,
                    template_id=resolve_template_id("amber", reasons, config_path=self.template_map_path),
                    hold_minutes=0,
                    score=0.70,
                    elevated_families_count=0,
                    family_flags={"A": False, "B": False, "C": False, "D": False},
                    applied_rules=applied_rules
                )
            except Exception:
                has_error_or_timeout = True
                applied_rules.append("scoring_exception_occurred")

        if has_error_or_timeout:
            # Fail-open with device-only check
            applied_rules.append("fail_open_device_check")
            reasons = []
            if features.get("screen_shared", False):
                reasons.append("SCREEN_SHARED")
            if features.get("remote_app_new", False):
                reasons.append("REMOTE_APP_NEW")
            elif features.get("remote_app_present", False):
                reasons.append("REMOTE_APP_ACTIVE")
            if features.get("on_call", False):
                reasons.append("ON_CALL")
            # Checks that need no model still run: a reported payee, a known-bad link, a large first
            # payment to a stranger.
            if (features.get("payee_reports_prior") or 0) > 0:
                reasons.append("PAYEE_REPORTED")
            if features.get("link_bad") == 1:
                reasons.append("BAD_LINK")
            if self._large_first_payment_to_stranger(features, trusted_payee_history):
                reasons.append("NEW_PAYEE")

            # In fail-open, if critical device compromise is present, raise amber caution, else green
            if reasons:
                tier = "amber"
                template_id = resolve_template_id("amber", reasons, config_path=self.template_map_path)
            else:
                tier = "green"
                template_id = resolve_template_id("green", [], is_silent_pass=False, config_path=self.template_map_path)

            return PolicyDecision(
                tier=tier,
                reasons=reasons if tier != "green" else [],
                template_id=template_id,
                hold_minutes=0,
                score=0.30 if tier == "amber" else 0.05,
                elevated_families_count=1 if reasons else 0,
                family_flags={"A": bool(reasons), "B": False, "C": False, "D": False},
                applied_rules=applied_rules
            )

        assert fusion_score_val is not None

        # ---------------------------------------------------------------------
        # Step 5: Corroboration Rule & Tier Assignment
        # ---------------------------------------------------------------------
        fam_thresholds = self.config.get("family_thresholds", {
            "A": 0.40, "B": 0.40, "C": 0.35, "D": 0.35
        })

        if score_res and score_res.family_contrib:
            fam_contrib = score_res.family_contrib
        else:
            fam_contrib = self.compute_family_contributions(features)

        family_flags = {
            fam: (fam_contrib.get(fam, 0.0) >= thresh)
            for fam, thresh in fam_thresholds.items()
        }
        elevated_families_count = sum(1 for triggered in family_flags.values() if triggered)

        # Retrieve thresholds from scorer if scored with SatarkScorer, else config
        if isinstance(raw_out, dict) and hasattr(self.scorer, "thr") and isinstance(self.scorer.thr, dict):
            amber_thresh = float(self.scorer.thr.get("amber", 0.6912))
            red_thresh = float(self.scorer.thr.get("red", 0.9891))
        else:
            amber_thresh = float(self.config.get("amber_threshold", 0.35))
            red_thresh = float(self.config.get("red_threshold", 0.50))

        reasons = list(model_reasons)
        if features.get("on_call") and "ON_CALL" not in reasons:
            reasons.insert(0, "ON_CALL")
        if features.get("screen_shared") and "SCREEN_SHARED" not in reasons:
            reasons.insert(0, "SCREEN_SHARED")
        if features.get("remote_app_new") and "REMOTE_APP_NEW" not in reasons:
            reasons.insert(0, "REMOTE_APP_NEW")
        elif features.get("remote_app_present") and "REMOTE_APP_PRESENT" not in reasons and "REMOTE_APP_ACTIVE" not in reasons:
            reasons.insert(0, "REMOTE_APP_PRESENT")

        is_red_candidate = (fusion_score_val >= red_thresh) or (tier_hint == "red")
        # Amber needs the model's amber threshold or a strong coercion signal. Two families firing
        # is no longer enough on its own: on the validation world (seed 33) that rule warned on
        # about 15,900 genuine payments and caught 1 scam the model missed (ml/eval_log.md).
        # Screen sharing or a new remote-access app warns on its own, except for a payee the user has
        # paid before over at least a week while no unknown caller is on the line: family helping by
        # screen share caused about 3 in 4 false alarms on the validation worlds, and money sent to an
        # established payee is not where a remote scammer can take it. A same-day "Rs 1 test"
        # payment does not make a payee established.
        known = self.config.get("coercion_known_payee", {})
        paid_before, paid_over_days = trusted_payee_history or (0, 0)
        unknown_caller = bool(features.get("on_call")) and not features.get("caller_in_contacts")
        established_payee = paid_before >= known.get("min_payments", 2) and \
            paid_over_days >= known.get("min_history_days", 7)
        has_strong_signal = strong_coercion(features) and not (established_payee and not unknown_caller)
        is_amber_candidate = (
            (fusion_score_val >= amber_thresh)
            or (tier_hint in ("amber", "red"))
            or has_strong_signal
            # Server link intelligence marks the domain as known bad: never green, whatever the model
            # makes of the rest (a "safe" note pulled a bad link on a live call down to green).
            or features.get("link_bad") == 1
        )

        if elevated_families_count >= 2 and is_red_candidate:
            tier = "red"
            hold_minutes = int(self.config.get("hold_minutes", 30))
            applied_rules.append("red_corroboration_met")
        elif is_amber_candidate:
            tier = "amber"
            hold_minutes = 0
            applied_rules.append("amber_threshold_met")
        elif self._large_first_payment_to_stranger(features, trusted_payee_history):
            # Safety net the model does not provide: it learned that big first payments to people are
            # usually legitimate (emergencies, purchases), so ₹50,000 to an unknown number scored green.
            # On the validation worlds this costs about 0.4 to 0.5 extra warnings per 1,000 payments.
            tier = "amber"
            hold_minutes = 0
            applied_rules.append("large_first_payment_to_stranger")
            # AMOUNT_UNUSUAL only when it is true for this user (same test as the scorer's reasons).
            unusual = float(features.get("amount_ratio") or 0) >= 2 or float(features.get("amount_z") or 0) >= 2
            for code in (["AMOUNT_UNUSUAL"] if unusual else []) + ["NEW_PAYEE"]:
                if code not in reasons:
                    reasons.append(code)
        elif self._suspicious_collect(features):
            # "Approve to RECEIVE money": a collect request takes money from the user. From an
            # unverified requester with a receive/refund story it is the classic collect scam.
            tier = "amber"
            hold_minutes = 0
            applied_rules.append("suspicious_collect_request")
            if "COLLECT_REQUEST" not in reasons:
                reasons.insert(0, "COLLECT_REQUEST")
        elif self._unknown_caller_new_payee(features, fusion_score_val):
            # A caller who is not a saved contact, a first-time payee and an unusually large amount:
            # the coached-transfer shape under the stranger floor, where the model alone stays green.
            tier = "amber"
            hold_minutes = 0
            applied_rules.append("unknown_caller_new_payee")
            for code in ("ON_CALL", "NEW_PAYEE", "AMOUNT_UNUSUAL"):
                if code not in reasons:
                    reasons.append(code)
        else:
            tier = "green"
            hold_minutes = 0
            applied_rules.append("green_below_threshold")

        # (There is no weekly warning cap any more. Once ambers come only from the model or from
        # screen sharing / remote access, the cap's only effect was hiding real warnings on the later
        # payments of a multi-step scam.)

        # ---------------------------------------------------------------------
        # Step 6b: Vouched-for payee (trust already dropped if the payee was reported since, or is
        # over 90 days old). A user's "This was me" lowers only later ambers for this payee; an
        # analyst-accepted appeal also lowers red. Neither applies while a call, screen share or
        # remote-access app is active: a scammer could be steering this payment. A declined payee
        # was already returned in step 1.
        # ---------------------------------------------------------------------
        lowerable = ("amber", "red") if pair_trust == "analyst" else ("amber",) if pair_trust == "user" else ()
        if pair_trust == "user":
            # "This was me" covers about what the user saw: not a much larger amount (a task scam's
            # escalating steps), a known-bad link or a scam-story note.
            # A vouch with no known amount covers nothing; payments split within 24 hours count together.
            cap = float(self.config.get("vouch_max_amount_ratio", 1.5)) * float(vouched_amount or 0)
            sent = float(features.get("amount") or 0) + float(features.get("same_payee_sum_24h") or 0)
            if vouched_amount is None or sent > cap \
                    or features.get("link_bad") == 1 or features.get("note_intent") in SUSPICIOUS_INTENTS:
                lowerable = ()
        if tier in lowerable and not has_family_a:
            applied_rules.append(f"{pair_trust}_vouched_payee_green")
            tier, hold_minutes, reasons = "green", 0, []

        # ---------------------------------------------------------------------
        # Step 7: Red-tier Questionnaire (can only raise risk, never lower it)
        # ---------------------------------------------------------------------
        tier, reasons, hold_minutes = apply_questionnaire(
            tier, reasons, hold_minutes, questionnaire_answers, self.config, applied_rules
        )

        # Strict response rule: Only include reasons when tier is amber or red
        if tier == "green":
            reasons = []

        template_id = resolve_template_id(
            tier=tier,
            reasons=reasons,
            is_silent_pass=False,
            config_path=self.template_map_path
        )

        if not score_res:
            score_res = ScoreResult(
                score=round(fusion_score_val, 4),
                family_contrib=fam_contrib,
                top_reasons=reasons
            )

        return PolicyDecision(
            tier=tier,
            reasons=reasons,
            template_id=template_id,
            hold_minutes=hold_minutes,
            score=fusion_score_val,
            elevated_families_count=elevated_families_count,
            family_flags=family_flags,
            applied_rules=applied_rules,
            raw_score_result=score_res
        )

