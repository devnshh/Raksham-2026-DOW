"""
Payment-note intent. Only this label is used for scoring and stored as evidence;
the raw note text is never persisted. The Android SDK computes the same label on
the phone (risk-sdk NoteIntent.kt) and sends only the label.
"""

from typing import Optional

VALID_NOTE_INTENTS = {
    "none", "food", "home", "family", "misc", "task",
    "kyc", "legal", "investment", "refund", "receive"
}

# Intents that point at a known scam story (Family C).
SUSPICIOUS_INTENTS = {"task", "kyc", "legal", "investment", "refund", "receive"}

# Checked in order; first match wins. Keep in sync with NoteIntent.kt.
_KEYWORDS = (
    ("kyc", ("kyc", "verification", "verify")),
    ("food", ("dinner", "food", "lunch", "split")),
    ("home", ("rent", "home", "flat")),
    ("legal", ("cbi", "police", "legal", "court", "arrest")),
    ("investment", ("investment", "profit", "trading", "ipo")),
    ("refund", ("refund", "cashback", "rebate")),
    ("task", ("task", "commission", "deposit")),
    ("receive", ("receive",)),
    ("family", ("family",)),
)


def resolve_note_intent(note_intent: Optional[str], note_text: Optional[str]) -> str:
    """Returns a valid intent label: the client's label if valid, else one derived from the text."""
    label = (note_intent or "").strip().lower()
    if label in VALID_NOTE_INTENTS:
        return label
    text = (note_text or "").lower()
    for intent, words in _KEYWORDS:
        if any(w in text for w in words):
            return intent
    return "none"
