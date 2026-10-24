"""
Ground-truth brand look-alike and confusable detection for UPI VPAs.
Implements the exact logic and confusable mappings as in satark_sim.py / LookalikeDetector.kt.
"""

import re
from typing import List, Dict

KNOWN_BRANDS: List[str] = [
    "sbi", "hdfc", "icici", "axis", "paytm", "phonepe", "gpay", "amazon",
    "flipkart", "irctc", "airtel", "jio", "lic", "uidai", "incometax",
    "npci", "rbi", "myntra", "swiggy", "zomato", "police", "cbi", "cybercrime"
]

CONFUSABLE_MAP: Dict[str, str] = {
    '0': 'o',
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's'
}

_CONFUSABLE_TRANS = str.maketrans("01345", "oieas")
_TOKEN_SPLIT_REGEX = re.compile(r"[^a-z0-9]+")


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between s1 and s2."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )

    return dp[m][n]


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculates normalized Levenshtein similarity between [0.0, 1.0]."""
    if s1 == s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return max(0.0, 1.0 - (dist / max_len))


def compute_lookalike_score(handle: str, is_verified: bool = False) -> float:
    """
    Computes lookalike similarity score between 0.0 and 1.0.
    Verified merchants score 0.0 because an official registered handle is legitimate.
    """
    if is_verified:
        return 0.0

    if not handle or "@" not in handle:
        handle_prefix = handle.lower() if handle else ""
    else:
        handle_prefix = handle.split("@")[0].lower()

    # Split by non-alphanumeric punctuation
    tokens = _TOKEN_SPLIT_REGEX.split(handle_prefix)
    max_ratio = 0.0

    for token in tokens:
        if len(token) < 3:
            continue

        # Fold confusables: 0->o, 1->i, 3->e, 4->a, 5->s
        folded = token.translate(_CONFUSABLE_TRANS)

        for brand in KNOWN_BRANDS:
            # Direct exact match on token
            if folded == brand:
                return 1.0

            ratio = levenshtein_similarity(folded, brand)
            if ratio > max_ratio:
                max_ratio = ratio

    return round(max_ratio, 2)

