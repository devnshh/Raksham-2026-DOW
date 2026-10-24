"""Lookalike detection package."""
from api.lookalike.detector import compute_lookalike_score, KNOWN_BRANDS, CONFUSABLE_MAP

__all__ = ["compute_lookalike_score", "KNOWN_BRANDS", "CONFUSABLE_MAP"]

