"""
Bridge module forwarding to model_service.satark_scorer.
Preserved for backward-compatibility.
"""
from model_service.satark_scorer import (
    SatarkScorer,
    INTENT_TEXT,
    REASON_MAP,
    LINK_COLS,
    make_thresholds
)

__all__ = [
    "SatarkScorer",
    "INTENT_TEXT",
    "REASON_MAP",
    "LINK_COLS",
    "make_thresholds"
]
