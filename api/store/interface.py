"""
Feature Store Abstract Interface.
Keeps the feature store behind an interface so Redis/DynamoDB can replace it.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List


class BaseFeatureStore(ABC):
    """Abstract interface for SATARK feature store and payee registry."""

    @abstractmethod
    def compute_baseline_features(
        self,
        user_id: str,
        payee_vpa: str,
        amount: float,
        current_hour: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes baseline features point-in-time from user's rolling 90-day history:
        amount_ratio, amount_z, amount_vs_max, hour_familiarity, baseline_ready,
        same_payee_count_24h, same_payee_sum_24h, escalation_ratio, payee_first_time.
        """
        pass

    @abstractmethod
    def compute_timing_z_scores(
        self,
        user_id: str,
        typing_ms: float,
        pauses: int,
        pin_secs: float
    ) -> Dict[str, float]:
        """
        Computes robust z-scores (median & MAD) for typing, pauses, and PIN duration
        relative to user's last 50 session dynamics.
        """
        pass

    @abstractmethod
    def get_payee_profile(self, payee_vpa: str) -> Dict[str, Any]:
        """
        Queries payee registry for payee features:
        payee_age_days, payee_verified, payee_new_payers_24h, payee_reports_prior,
        lookalike_score, is_confirmed_scam, confirmations.
        Unknown payees return 'unknown' characteristics, never safe defaults.
        """
        pass

    @abstractmethod
    def get_trusted_payee_history(self, user_id: str, payee_vpa: str) -> Tuple[int, int]:
        """
        Returns (transaction_count, history_days) between user and payee.
        """
        pass

    @abstractmethod
    def record_case(
        self,
        case_id: str,
        txn_ref: Optional[str],
        user_id: str,
        payee_vpa: str,
        amount: float,
        tier: str,
        reasons: List[str],
        template_id: str,
        hold_minutes: int,
        feature_vector: Dict[str, Any],
        evidence_pack: Dict[str, Any]
    ) -> None:
        """Stores case record and evidence pack."""
        pass

    @abstractmethod
    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific case by case_id."""
        pass

    @abstractmethod
    def list_cases(
        self,
        tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Lists cases optionally filtered by tier."""
        pass

    @abstractmethod
    def record_report(
        self,
        report_id: str,
        reporter_id: str,
        payee_vpa: str,
        reason: str,
        notes: Optional[str]
    ) -> int:
        """Records user report and increments payee prior_reports_count. Returns new report count."""
        pass

    @abstractmethod
    def confirm_scam_payee(
        self,
        payee_vpa: str,
        analyst_id: str,
        notes: Optional[str]
    ) -> Tuple[int, bool]:
        """
        Adds analyst confirmation.
        Requires TWO distinct analyst IDs before is_confirmed_scam becomes True.
        Returns (total_distinct_confirmations, is_confirmed_scam).
        """
        pass
