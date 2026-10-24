"""
Scorer interface and Stub implementation for SATARK.
Pure Python, NO FastAPI dependencies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path

from api.policy.intent import SUSPICIOUS_INTENTS

from api.model_client import (
    ModelClient,
    LocalModelClient,
    HttpModelClient,
    get_model_client,
    ModelServiceError,
    ModelValidationError,
    ModelTimeoutError,
    ModelConnectionError
)

_satark_scorer_instance: Optional[ModelClient] = None


def get_satark_scorer(
    model_path: Optional[str] = None,
    thresholds_path: Optional[str] = None
) -> ModelClient:
    """Module-level singleton loader returning the active ModelClient."""
    global _satark_scorer_instance
    if _satark_scorer_instance is None:
        _satark_scorer_instance = get_model_client()
    return _satark_scorer_instance


@dataclass
class ScoreResult:
    """Output contract of the scorer."""
    score: float
    family_contrib: Dict[str, float] = field(default_factory=dict)
    top_reasons: List[str] = field(default_factory=list)


class BaseScorer(ABC):
    """Abstract interface for all SATARK scorers."""

    @abstractmethod
    def score(self, features: Dict[str, Any]) -> ScoreResult:
        """Computes risk score, family contributions, and top reasons from features."""
        pass


class StubScorer(BaseScorer):
    """
    Weighted rule-based stub scorer implementing the baseline heuristic logic.
    Replaced by XGBoost model in later stages.
    """

    def score(self, features: Dict[str, Any]) -> ScoreResult:
        reasons: List[str] = []

        # ---------------------------------------------------------------------
        # Family A: Session Coercion
        # ---------------------------------------------------------------------
        fam_a = 0.0
        if features.get("on_call", False):
            fam_a += 0.15 if features.get("caller_in_contacts") else 0.45
            reasons.append("ON_CALL")

        if features.get("screen_shared", False):
            fam_a += 0.50
            reasons.append("SCREEN_SHARED")

        remote_present = features.get("remote_app_present", False)
        remote_new = features.get("remote_app_new", False)
        if remote_present or remote_new:
            fam_a += 0.55 if remote_new else 0.35
            reasons.append("REMOTE_APP_NEW" if remote_new else "REMOTE_APP_ACTIVE")

        typing_z = float(features.get("typing_z", 0.0))
        pause_z = float(features.get("pause_z", 0.0))
        if typing_z >= 1.5 or pause_z >= 2.0:
            fam_a += 0.25
            reasons.append("ABNORMAL_HESITATION")

        pin_time_z = float(features.get("pin_time_z", 0.0))
        if pin_time_z >= 2.0:
            fam_a += 0.20
            reasons.append("PIN_TIME_EXTENDED")

        # ---------------------------------------------------------------------
        # Family B: Payee Risk
        # ---------------------------------------------------------------------
        fam_b = 0.0
        first_time = features.get("payee_first_time", False)
        payee_age = float(features.get("payee_age_days", 365.0))
        if first_time:
            fam_b += 0.20
            reasons.append("PAYEE_FIRST_TIME")
            if payee_age <= 30.0:
                fam_b += 0.35
                reasons.append("NEW_PAYEE_YOUNG_ACCOUNT")

        new_payers = int(features.get("payee_new_payers_24h", 0))
        verified = features.get("payee_verified", False)
        if new_payers >= 5 and not verified:
            fam_b += 0.40
            reasons.append("MANY_NEW_PAYERS")

        reports = int(features.get("payee_reports_prior", 0))
        if reports >= 1:
            fam_b += 0.50
            reasons.append("REPORTED_BY_OTHERS")

        lookalike = float(features.get("lookalike_score", 0.0))
        if lookalike >= 0.70:
            fam_b += 0.45
            reasons.append("LOOKALIKE_HANDLE")

        # ---------------------------------------------------------------------
        # Family C: Context
        # ---------------------------------------------------------------------
        fam_c = 0.0
        if features.get("link_bad") is True:
            fam_c += 0.55
            reasons.append("MALICIOUS_LINK_ORIGIN")

        domain_age = features.get("link_domain_age_days")
        if domain_age is not None and float(domain_age) < 15.0:
            fam_c += 0.30

        # Only the note's intent label is used; raw note text never reaches scoring.
        if str(features.get("note_intent") or "").lower() in SUSPICIOUS_INTENTS:
            fam_c += 0.30
            reasons.append("NOTE_INTENT_RISK")

        # ---------------------------------------------------------------------
        # Family D: User Baseline
        # ---------------------------------------------------------------------
        fam_d = 0.0
        amount_ratio = float(features.get("amount_ratio", 1.0))
        amount_z = float(features.get("amount_z", 0.0))

        if amount_ratio >= 4.0 or amount_z >= 2.5:
            fam_d += 0.45
            reasons.append("AMOUNT_UNUSUAL")
        elif amount_ratio >= 2.5:
            fam_d += 0.25

        escalation = float(features.get("escalation_ratio", 1.0))
        same_payee_count = int(features.get("same_payee_count_24h", 0))
        if escalation >= 2.0 and same_payee_count >= 1:
            fam_d += 0.40
            reasons.append("ESCALATING_PAYMENTS")

        # Composite score
        composite_score = min(
            1.0,
            (fam_a * 0.35) + (fam_b * 0.35) + (fam_c * 0.15) + (fam_d * 0.25)
        )

        family_contrib = {
            "A": round(fam_a, 3),
            "B": round(fam_b, 3),
            "C": round(fam_c, 3),
            "D": round(fam_d, 3)
        }

        # Deduplicate reasons while preserving order
        seen = set()
        deduped_reasons = []
        for r in reasons:
            if r not in seen:
                seen.add(r)
                deduped_reasons.append(r)

        return ScoreResult(
            score=round(composite_score, 3),
            family_contrib=family_contrib,
            top_reasons=deduped_reasons
        )

