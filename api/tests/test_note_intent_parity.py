"""The phone (NoteIntent.kt) and the server/evaluation (api/policy/intent.py) must label notes identically."""
import re
from pathlib import Path

from api.policy.intent import _KEYWORDS, resolve_note_intent

KOTLIN = Path(__file__).resolve().parents[2] / "risk-sdk/src/main/java/com/raksham/risk/session/NoteIntent.kt"


def kotlin_keywords():
    pairs = re.findall(r'"(\w+)" to listOf\(([^)]*)\)', KOTLIN.read_text())
    return tuple((intent, tuple(re.findall(r'"([^"]+)"', words))) for intent, words in pairs)


def test_keyword_rules_match_kotlin_in_order():
    assert kotlin_keywords() == _KEYWORDS


def test_label_comes_from_text_not_from_ground_truth():
    # Scam notes the keyword rules miss stay "none", exactly as on the phone.
    assert resolve_note_intent(None, "case clearance") == "none"
    assert resolve_note_intent(None, "rbi safe account") == "none"
    assert resolve_note_intent(None, "KYC UPDATE FEE ji") == "kyc"
