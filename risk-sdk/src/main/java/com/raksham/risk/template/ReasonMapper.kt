package com.raksham.risk.template

import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.model.PlainReason

object ReasonMapper {

    private val REASON_MAP = mapOf(
        "ON_CALL" to PlainReason(
            en = "Active phone call detected during payment",
            hi = "भुगतान के दौरान सक्रिय फोन कॉल का पता चला"
        ),
        "SCREEN_SHARED" to PlainReason(
            en = "Screen is currently being shared or recorded",
            hi = "आपकी स्क्रीन साझा या रिकॉर्ड की जा रही है"
        ),
        "REMOTE_APP_ACTIVE" to PlainReason(
            en = "Remote control application detected",
            hi = "रिमोट कंट्रोल ऐप चालू पाया गया"
        ),
        "REMOTE_APP_NEW" to PlainReason(
            en = "Remote access application installed within last 24 hours",
            hi = "रिमोट एक्सेस ऐप पिछले 24 घंटों में इंस्टॉल किया गया है"
        ),
        "ABNORMAL_HESITATION" to PlainReason(
            en = "Unusual hesitation and slow typing detected",
            hi = "आपकी सामान्य टाइपिंग गति की तुलना में असामान्य झिझक"
        ),
        "PIN_TIME_EXTENDED" to PlainReason(
            en = "Unusually long time spent confirming payment",
            hi = "पुष्टिकरण पर सामान्य से अधिक समय बिताया गया"
        ),
        "PAYEE_FIRST_TIME" to PlainReason(
            en = "First time transferring money to this beneficiary",
            hi = "इस लाभार्थी को पहली बार पैसे भेजे जा रहे हैं"
        ),
        "NEW_PAYEE_YOUNG_ACCOUNT" to PlainReason(
            en = "Beneficiary account was created very recently",
            hi = "लाभार्थी का खाता बहुत हाल ही में बनाया गया है"
        ),
        "MANY_NEW_PAYERS" to PlainReason(
            en = "Unusual number of new payers sending money to this account",
            hi = "24 घंटों में इस खाते में कई नए लोगों द्वारा पैसे भेजे गए हैं"
        ),
        "HIGH_FAN_IN_MULE_PATTERN" to PlainReason(
            en = "Unusual number of new payers sending money to this account",
            hi = "24 घंटों में इस खाते में कई नए लोगों द्वारा पैसे भेजे गए हैं"
        ),
        "REPORTED_BY_OTHERS" to PlainReason(
            en = "Beneficiary has previous scam complaints reported",
            hi = "इस खाते के खिलाफ पूर्व में धोखाधड़ी की शिकायतें दर्ज हैं"
        ),
        "PRIOR_SCAM_REPORTS" to PlainReason(
            en = "Beneficiary has previous scam complaints reported",
            hi = "इस खाते के खिलाफ पूर्व में धोखाधड़ी की शिकायतें दर्ज हैं"
        ),
        "LOOKALIKE_HANDLE" to PlainReason(
            en = "UPI handle mimics a known organization or brand",
            hi = "यूपीआई आईडी किसी बैंक या प्रसिद्ध कंपनी की नकल प्रतीत होती है"
        ),
        "LOOKALIKE_BRAND_HANDLE" to PlainReason(
            en = "UPI handle mimics a known organization or brand",
            hi = "यूपीआई आईडी किसी बैंक या प्रसिद्ध कंपनी की नकल प्रतीत होती है"
        ),
        "AMOUNT_8X_USUAL" to PlainReason(
            en = "Transfer amount is significantly higher than your typical transactions",
            hi = "यह राशि आपके सामान्य लेनदेन से काफी अधिक है"
        ),
        "AMOUNT_HIGH_VS_BASELINE" to PlainReason(
            en = "Transfer amount is significantly higher than your typical transactions",
            hi = "यह राशि आपके सामान्य लेनदेन से काफी अधिक है"
        ),
        "ESCALATING_PAYMENTS" to PlainReason(
            en = "Multiple transfers to this recipient in rapid succession",
            hi = "इस प्राप्तकर्ता को बार-बार भुगतान किए जा रहे हैं"
        ),
        "RAPID_ESCALATION" to PlainReason(
            en = "Multiple transfers to this recipient in rapid succession",
            hi = "इस प्राप्तकर्ता को बार-बार भुगतान किए जा रहे हैं"
        ),
        "MALICIOUS_LINK_ORIGIN" to PlainReason(
            en = "Payment originated from an unverified or risky external web link",
            hi = "भुगतान किसी असुरक्षित या संदिग्ध लिंक द्वारा शुरू किया गया था"
        ),
        "SUSPICIOUS_NOTE_TEXT" to PlainReason(
            en = "Payment note contains high-risk keywords",
            hi = "भुगतान नोट में संदिग्ध शब्द पाए गए"
        ),
        // Codes produced by the fusion model and the questionnaire. Without these the user saw a
        // vague "Unusual payment activity" instead of the real reason.
        "NEW_PAYEE" to PlainReason(
            en = "First time paying this account",
            hi = "इस खाते में पहली बार भुगतान"
        ),
        "UNVERIFIED_PAYEE" to PlainReason(
            en = "This account is not a verified merchant",
            hi = "यह खाता सत्यापित व्यापारी नहीं है"
        ),
        "FAN_IN_24H" to PlainReason(
            en = "Unusual number of new payers sending money to this account",
            hi = "24 घंटों में इस खाते में कई नए लोगों द्वारा पैसे भेजे गए हैं"
        ),
        "PAYEE_REPORTED" to PlainReason(
            en = "Other users have reported this account as a scam",
            hi = "अन्य उपयोगकर्ताओं ने इस खाते की धोखाधड़ी के रूप में शिकायत की है"
        ),
        "AMOUNT_UNUSUAL" to PlainReason(
            en = "Transfer amount is significantly higher than your typical transactions",
            hi = "यह राशि आपके सामान्य लेनदेन से काफी अधिक है"
        ),
        "UNUSUAL_HOUR" to PlainReason(
            en = "You rarely make payments at this time of day",
            hi = "आप आमतौर पर इस समय भुगतान नहीं करते"
        ),
        "BAD_LINK" to PlainReason(
            en = "The link that opened this payment is known to be unsafe or very new",
            hi = "जिस लिंक से यह भुगतान शुरू हुआ वह असुरक्षित या बहुत नया है"
        ),
        "COLLECT_REQUEST" to PlainReason(
            en = "This is a request to take money from you. Approving it sends money; it never receives any",
            hi = "यह आपसे पैसे लेने का अनुरोध है। मंज़ूरी देने पर पैसे आपके खाते से जाएंगे, आएंगे नहीं"
        ),
        "LINK_ENTRY" to PlainReason(
            en = "This payment was opened from a link",
            hi = "यह भुगतान एक लिंक से खोला गया"
        ),
        "QR_ENTRY" to PlainReason(
            en = "This payment was started from a QR code",
            hi = "यह भुगतान एक QR कोड से शुरू हुआ"
        ),
        "REPEAT_PAYEE_24H" to PlainReason(
            en = "Several payments to this account in the last 24 hours",
            hi = "पिछले 24 घंटों में इस खाते को कई भुगतान"
        ),
        "NOTE_INTENT_RISK" to PlainReason(
            en = "The payment note matches a common scam story (refund, KYC, police, task)",
            hi = "भुगतान नोट किसी आम धोखाधड़ी कहानी से मेल खाता है (रिफंड, केवाईसी, पुलिस, टास्क)"
        ),
        "SESSION_PRESSURE" to PlainReason(
            en = "You seem to be switching apps or pausing more than usual",
            hi = "आप सामान्य से अधिक ऐप बदल रहे हैं या रुक रहे हैं"
        ),
        "FAILED_AUTH" to PlainReason(
            en = "Recent failed PIN attempts",
            hi = "हाल में पिन के असफल प्रयास"
        ),
        "NEW_DEVICE" to PlainReason(
            en = "This phone was recently set up for your account",
            hi = "यह फोन हाल ही में आपके खाते के लिए सेट किया गया"
        ),
        "REMOTE_APP_PRESENT" to PlainReason(
            en = "A remote-access app is installed on this phone",
            hi = "इस फोन पर रिमोट एक्सेस ऐप इंस्टॉल है"
        ),
        "USER_REPORTED_GUIDANCE" to PlainReason(
            en = "You told us someone is guiding you through this payment",
            hi = "आपने बताया कि कोई आपको यह भुगतान करने के लिए निर्देश दे रहा है"
        ),
        "ANALYST_CONFIRMED_SCAM" to PlainReason(
            en = "Beneficiary has been confirmed as a fraudulent account",
            hi = "इस खाते को धोखाधड़ी के रूप में सत्यापित किया गया है"
        ),
        "CHECK_UNAVAILABLE" to PlainReason(
            en = "We couldn't complete a safety check. Please confirm this payee before continuing.",
            hi = "हम सुरक्षा जांच पूरी नहीं कर सके। कृपया जारी रखने से पहले इस प्राप्तकर्ता की पुष्टि करें।"
        )
    )

    fun mapCodeToPlainReason(rawCode: String, payment: PaymentRequest? = null): PlainReason {
        val cleanCode = rawCode.trim().uppercase()
        return REASON_MAP[cleanCode] ?: PlainReason(
            en = "Unusual payment activity detected.",
            hi = "असामान्य भुगतान गतिविधि का पता चला।"
        )
    }
}
