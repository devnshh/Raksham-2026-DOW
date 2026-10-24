"""
Fixed message templates in English and Hindi for SATARK.
Strictly NO LLM, NO free-form text in user-facing paths.
"""

from typing import Dict, Any

# Reason Code mapping to English and Hindi descriptions
REASON_TEMPLATES: Dict[str, Dict[str, str]] = {
    "ON_CALL": {
        "en": "Active phone call detected during payment",
        "hi": "भुगतान के दौरान सक्रिय फोन कॉल का पता चला"
    },
    "SCREEN_SHARED": {
        "en": "Screen is currently being shared or recorded",
        "hi": "आपकी स्क्रीन साझा या रिकॉर्ड की जा रही है"
    },
    "REMOTE_APP_ACTIVE": {
        "en": "Remote desktop or screen control application active",
        "hi": "रिमोट कंट्रोल ऐप चालू पाया गया"
    },
    "REMOTE_APP_NEW": {
        "en": "Remote access application installed within last 24 hours",
        "hi": "रिमोट एक्सेस ऐप पिछले 24 घंटों में इंस्टॉल किया गया है"
    },
    "ABNORMAL_HESITATION": {
        "en": "Abnormal pauses and slow typing compared to your normal rhythm",
        "hi": "आपकी सामान्य टाइपिंग गति की तुलना में असामान्य झिझक"
    },
    "PIN_TIME_EXTENDED": {
        "en": "Unusually long time spent on the PIN confirmation step",
        "hi": "पिन पुष्टिकरण पर सामान्य से अधिक समय बिताया गया"
    },
    "PAYEE_FIRST_TIME": {
        "en": "First time transferring money to this beneficiary",
        "hi": "इस लाभार्थी को पहली बार पैसे भेजे जा रहे हैं"
    },
    "NEW_PAYEE_YOUNG_ACCOUNT": {
        "en": "Beneficiary account was created very recently",
        "hi": "लाभार्थी का खाता बहुत हाल ही में बनाया गया है"
    },
    "MANY_NEW_PAYERS": {
        "en": "Unusual influx of many first-time payers to this beneficiary in 24 hours",
        "hi": "24 घंटों में इस खाते में कई नए लोगों द्वारा पैसे भेजे गए हैं (म्यूल पैटर्न)"
    },
    "HIGH_FAN_IN_MULE_PATTERN": {
        "en": "Unusual influx of many first-time payers to this beneficiary in 24 hours",
        "hi": "24 घंटों में इस खाते में कई नए लोगों द्वारा पैसे भेजे गए हैं (म्यूल पैटर्न)"
    },
    "REPORTED_BY_OTHERS": {
        "en": "Beneficiary has previous scam complaints lodged on cybercrime portals",
        "hi": "इस खाते के खिलाफ साइबर अपराध पोर्टल पर पूर्व धोखाधड़ी की शिकायतें हैं"
    },
    "PRIOR_SCAM_REPORTS": {
        "en": "Beneficiary has previous scam complaints lodged on cybercrime portals",
        "hi": "इस खाते के खिलाफ साइबर अपराध पोर्टल पर पूर्व धोखाधड़ी की शिकायतें हैं"
    },
    "LOOKALIKE_HANDLE": {
        "en": "UPI handle mimics a well-known brand or government body",
        "hi": "यूपीआई आईडी किसी बैंक या प्रसिद्ध कंपनी की नकल प्रतीत होती है"
    },
    "LOOKALIKE_BRAND_HANDLE": {
        "en": "UPI handle mimics a well-known brand or government body",
        "hi": "यूपीआई आईडी किसी बैंक या प्रसिद्ध कंपनी की नकल प्रतीत होती है"
    },
    "AMOUNT_8X_USUAL": {
        "en": "Amount is significantly higher than your typical 90-day transactions",
        "hi": "यह राशि आपके सामान्य 90-दिन के लेनदेन से काफी अधिक है"
    },
    "AMOUNT_HIGH_VS_BASELINE": {
        "en": "Amount is significantly higher than your typical 90-day transactions",
        "hi": "यह राशि आपके सामान्य 90-दिन के लेनदेन से काफी अधिक है"
    },
    "ESCALATING_PAYMENTS": {
        "en": "Consecutive transfers to this recipient are rapidly escalating in size",
        "hi": "इस प्राप्तकर्ता को बार-बार बढ़ती हुई राशि के भुगतान किए जा रहे हैं"
    },
    "RAPID_ESCALATION": {
        "en": "Consecutive transfers to this recipient are rapidly escalating in size",
        "hi": "इस प्राप्तकर्ता को बार-बार बढ़ती हुई राशि के भुगतान किए जा रहे हैं"
    },
    "MALICIOUS_LINK_ORIGIN": {
        "en": "Payment was initiated from an unverified or risky external web link",
        "hi": "भुगतान किसी असुरक्षित या संदिग्ध लिंक द्वारा शुरू किया गया था"
    },
    "SUSPICIOUS_NOTE_TEXT": {
        "en": "Payment note contains high-risk scam keywords (e.g. refund, KYC, CBI)",
        "hi": "भुगतान नोट में संदिग्ध शब्द पाए गए (जैसे 'रिफंड', 'केवाईसी', 'जाँच')"
    },
    "ANALYST_CONFIRMED_SCAM": {
        "en": "This beneficiary has been confirmed as a fraudulent mule account by security analysts",
        "hi": "सुरक्षा विश्लेषकों द्वारा इस खाते को धोखाधड़ी (म्यूल खाता) के रूप में चिह्नित किया गया है"
    }
}


# Tier templates metadata
TIER_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "green_silent_pass": {
        "template_id": "green_silent_pass",
        "headline_en": "Transaction Verified",
        "headline_hi": "लेनदेन सत्यापित",
        "explanation_en": "Normal payment to trusted beneficiary within baseline.",
        "explanation_hi": "विश्वसनीय लाभार्थी को सामान्य भुगतान।",
        "appeal_allowed": False
    },
    "green_pass_v1": {
        "template_id": "green_pass_v1",
        "headline_en": "Payment Safety Checked",
        "headline_hi": "भुगतान सुरक्षा जाँची गई",
        "explanation_en": "Beneficiary and session parameters are within normal personal baseline.",
        "explanation_hi": "लाभार्थी और सत्र आपके सामान्य व्यक्तिगत आधार के अनुकूल हैं।",
        "appeal_allowed": False
    },
    "amber_caution_v1": {
        "template_id": "amber_caution_v1",
        "headline_en": "Caution: Verify before you pay",
        "headline_hi": "सावधानी: भुगतान करने से पहले पुष्टि करें",
        "explanation_en": "You are paying a beneficiary with an unusual signal. Please confirm the recipient's identity.",
        "explanation_hi": "आप ऐसे व्यक्ति को पैसे भेज रहे हैं जहाँ एक असामान्य संकेत मिला है। कृपया पुष्टि करें।",
        "appeal_allowed": False
    },
    "red_coached_intervention_v1": {
        "template_id": "red_coached_intervention_v1",
        "headline_en": "Wait. This looks like a scam transfer.",
        "headline_hi": "रुकिए। यह धोखाधड़ी का लेनदेन प्रतीत होता है।",
        "explanation_en": "Satark detected multiple danger signals: You may be on an active call or being guided into transferring funds to an unverified new payee. Police and banks NEVER ask you to transfer funds for 'verification' or 'digital arrest'.",
        "explanation_hi": "सतर्क ने कई खतरे के संकेत पकड़े हैं: आप फोन कॉल पर हो सकते हैं या किसी के कहने पर अनजान खाते में पैसे भेज रहे हैं। पुलिस या बैंक कभी भी 'जाँच' या 'डिजिटल अरेस्ट' के लिए पैसे ट्रांसफर करने को नहीं कहते।",
        "appeal_allowed": True
    },
    "red_call_new_payee_v1": {
        "template_id": "red_call_new_payee_v1",
        "headline_en": "Wait. This looks like a scam call.",
        "headline_hi": "रुकिए। यह धोखाधड़ी का फोन कॉल प्रतीत होता है।",
        "explanation_en": "You are on a call right now and transferring money to a new, unverified account. Police and banks NEVER ask you to move money 'for verification'.",
        "explanation_hi": "आप इस समय कॉल पर हैं और एक नए असत्यापित खाते में पैसे भेज रहे हैं। पुलिस या बैंक कभी 'जाँच' के लिए पैसे ट्रांसफर करने को नहीं कहते।",
        "appeal_allowed": True
    },
    "decline_known_mule_v1": {
        "template_id": "decline_known_mule_v1",
        "headline_en": "Payment Blocked: High Risk Mule Account",
        "headline_hi": "भुगतान रोका गया: उच्च जोखिम वाला खाता",
        "explanation_en": "This UPI handle has been verified as a fraudulent account by bank security analysts. Contact support if you believe this is an error.",
        "explanation_hi": "इस यूपीआई आईडी को बैंक सुरक्षा विश्लेषकों द्वारा साइबर धोखाधड़ी के रूप में सत्यापित किया गया है। यदि यह त्रुटि है तो अपील करें।",
        "appeal_allowed": True,
        "appeal_path": "/v1/cases/{case_id}/appeal"
    }
}


def get_reason_text(code: str, lang: str = "en") -> str:
    """Returns bilingual description for reason code."""
    entry = REASON_TEMPLATES.get(code.upper())
    if entry:
        return entry.get(lang, entry.get("en", code))
    return code


import json
from pathlib import Path
from api.config import TEMPLATE_MAP_PATH

_TEMPLATE_MAP_CACHE: Dict[str, Any] | None = None


def load_template_map(path: str = TEMPLATE_MAP_PATH) -> Dict[str, Any]:
    """Loads and caches the reason code to template mapping config."""
    global _TEMPLATE_MAP_CACHE
    if _TEMPLATE_MAP_CACHE is None:
        p = Path(path)
        if p.exists():
            _TEMPLATE_MAP_CACHE = json.loads(p.read_text(encoding="utf-8"))
        else:
            _TEMPLATE_MAP_CACHE = {}
    return _TEMPLATE_MAP_CACHE


def resolve_template_id(
    tier: str,
    reasons: list[str],
    is_silent_pass: bool = False,
    config_path: str = TEMPLATE_MAP_PATH
) -> str:
    """Maps reason codes and tier to appropriate template_id using the small config file."""
    cfg = load_template_map(config_path)
    tier_map = cfg.get("tier_templates", {}).get(tier.lower(), {})
    priority = cfg.get("reason_priority", [])

    if tier.lower() == "green":
        if is_silent_pass:
            return tier_map.get("silent", "green_silent_pass")
        return tier_map.get("default", "green_pass_v1")

    # Check reasons against priority order and tier_map
    reasons_set = {r.upper() for r in reasons}
    for code in priority:
        if code.upper() in reasons_set and code.upper() in tier_map:
            return tier_map[code.upper()]

    # Check any reason directly in tier_map
    for r in reasons:
        ru = r.upper()
        if ru in tier_map:
            return tier_map[ru]

    return tier_map.get(
        "default",
        "decline_known_mule_v1" if tier == "decline" else
        "red_coached_intervention_v1" if tier == "red" else
        "amber_caution_v1" if tier == "amber" else
        "green_pass_v1"
    )

