"""
Payment-note intent. Only this label is used for scoring and stored as evidence;
the raw note text is never persisted. The Android SDK computes the same label on
the phone (risk-sdk NoteIntent.kt) and sends only the label.
"""

import re
from typing import Optional

VALID_NOTE_INTENTS = {
    "none", "food", "home", "family", "misc", "task",
    "kyc", "legal", "investment", "refund", "receive"
}

# Intents that point at a known scam story (Family C).
SUSPICIOUS_INTENTS = {"task", "kyc", "legal", "investment", "refund", "receive"}

# Checked in order; first match wins, so scam stories come before everyday words ("refund for
# parents" is a refund note, not rent). Keep in sync with NoteIntent.kt.
_KEYWORDS = (
    ("kyc", ("kyc", "verification", "verify")),
    ("legal", ("cbi", "police", "legal", "court", "arrest")),
    ("investment", ("investment", "profit", "trading", "ipo")),
    ("refund", ("refund", "cashback", "rebate")),
    ("task", ("task", "commission", "deposit")),
    ("receive", ("receive",)),
    ("food", ("dinner", "food", "lunch", "split")),
    ("home", ("rent", "home", "flat")),
    ("family", ("family",)),
)


def _words(text: str) -> set:
    """Whole words of a note, plus each word without a plural 's': a keyword must be a word of its own
    ("parents" is not "rent", "courtyard" is not "court"). Same rule in NoteIntent.kt."""
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return words | {w[:-1] for w in words if len(w) > 3 and w.endswith("s")}


def resolve_note_intent(note_intent: Optional[str], note_text: Optional[str]) -> str:
    """Returns a valid intent label: the client's label if valid, else one derived from the text."""
    label = (note_intent or "").strip().lower()
    if label in VALID_NOTE_INTENTS:
        return label
    words = _words(note_text or "")
    for intent, keywords in _KEYWORDS:
        if any(k in words for k in keywords):
            return intent
    return "none"
