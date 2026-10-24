"""
Unit tests for Lookalike and Confusable detection.
"""

from api.lookalike.detector import compute_lookalike_score


def test_verified_merchants_score_zero():
    """Verified merchants always score 0.0 regardless of name."""
    assert compute_lookalike_score("amazonpay@ybl", is_verified=True) == 0.0
    assert compute_lookalike_score("sbi.merchant@oksbi", is_verified=True) == 0.0
    assert compute_lookalike_score("police.welfare@sbi", is_verified=True) == 0.0


def test_confusable_digits_detection():
    """Detects homoglyphs with digit replacement: '0'->'o', '1'->'i', etc."""
    amaz0n_score = compute_lookalike_score("amaz0n-refund-desk@okaxis", is_verified=False)
    assert amaz0n_score >= 0.70, f"Expected amaz0n >= 0.70, got {amaz0n_score}"

    sb1_score = compute_lookalike_score("sb1-kyc-care@ybl", is_verified=False)
    assert sb1_score >= 0.70, f"Expected sb1 >= 0.70, got {sb1_score}"


def test_exact_brand_token_detection():
    """Detects direct brand words inside unverified handles."""
    cbi_score = compute_lookalike_score("cbi-verification-dept@ybl", is_verified=False)
    assert cbi_score == 1.0, f"Expected CBI token match == 1.0, got {cbi_score}"

    police_score = compute_lookalike_score("delhi-police-vault@okaxis", is_verified=False)
    assert police_score == 1.0, f"Expected police token match == 1.0, got {police_score}"


def test_regular_names_low_score():
    """Ordinary personal handles must not trigger false positives."""
    rahul_score = compute_lookalike_score("rahul.sharma@oksbi", is_verified=False)
    assert rahul_score < 0.40, f"Expected rahul.sharma < 0.40, got {rahul_score}"

    priya_score = compute_lookalike_score("priya.verma@okaxis", is_verified=False)
    assert priya_score < 0.40, f"Expected priya.verma < 0.40, got {priya_score}"

