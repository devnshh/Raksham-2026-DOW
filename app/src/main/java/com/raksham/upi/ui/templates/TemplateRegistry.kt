package com.raksham.upi.ui.templates

data class LocalTemplate(
    val templateId: String,
    val titleEn: String,
    val titleHi: String,
    val bodyEn: String,
    val bodyHi: String
)

object TemplateRegistry {

    private val TEMPLATES = mapOf(
        "amber_caution_v1" to LocalTemplate(
            templateId = "amber_caution_v1",
            titleEn = "Caution: Verify before you pay",
            titleHi = "सावधानी: भुगतान करने से पहले पुष्टि करें",
            bodyEn = "We noticed unusual details with this transaction. Please review the reasons below carefully before proceeding.",
            bodyHi = "हमने इस लेनदेन में असामान्य विवरण देखा है। कृपया आगे बढ़ने से पहले नीचे दिए गए कारणों की ध्यानपूर्वक समीक्षा करें।"
        ),
        "amber_lookalike_v1" to LocalTemplate(
            templateId = "amber_lookalike_v1",
            titleEn = "Caution: Possible Lookalike Account",
            titleHi = "सावधानी: संदिग्ध प्रतिरूप खाता",
            bodyEn = "This UPI address closely resembles a well-known organization or company. Verify that you are paying the official entity.",
            bodyHi = "यह यूपीआई पता किसी प्रसिद्ध संस्था से काफी मिलता-जुलता है। पुष्टि करें कि आप सही प्राप्तकर्ता को भेज रहे हैं।"
        ),
        "amber_unusual_amount_v1" to LocalTemplate(
            templateId = "amber_unusual_amount_v1",
            titleEn = "Caution: Unusual Transfer Amount",
            titleHi = "सावधानी: असामान्य भुगतान राशि",
            bodyEn = "This transfer amount is significantly higher than your typical transactions.",
            bodyHi = "यह भुगतान राशि आपके सामान्य लेनदेन से काफी अधिक है।"
        ),
        "amber_check_unavailable" to LocalTemplate(
            templateId = "amber_check_unavailable",
            titleEn = "Safety Check Unavailable",
            titleHi = "सुरक्षा जांच अनुपलब्ध",
            bodyEn = "We couldn't complete a safety check. Please confirm this payee before continuing.",
            bodyHi = "हम सुरक्षा जांच पूरी नहीं कर सके। कृपया जारी रखने से पहले इस प्राप्तकर्ता की पुष्टि करें।"
        ),
        "red_call_new_payee_v1" to LocalTemplate(
            templateId = "red_call_new_payee_v1",
            titleEn = "Wait. This looks like a scam call.",
            titleHi = "रुकिए। यह धोखाधड़ी का फोन कॉल प्रतीत होता है।",
            bodyEn = "You are on a call right now, and you are sending ₹{amount} to {payee}. You have never paid this account before.",
            bodyHi = "आप इस समय कॉल पर हैं, और आप {payee} को ₹{amount} भेज रहे हैं। आपने इस खाते में पहले कभी भुगतान नहीं किया है।"
        ),
        "red_coached_intervention_v1" to LocalTemplate(
            templateId = "red_coached_intervention_v1",
            titleEn = "Wait. This looks like a scam call.",
            titleHi = "रुकिए। यह धोखाधड़ी का फोन कॉल प्रतीत होता है।",
            bodyEn = "Multiple danger signals were detected during this transfer. Police and banks never ask you to move money 'for verification'.",
            bodyHi = "इस लेनदेन में कई खतरे के संकेत मिले हैं। पुलिस या बैंक कभी 'जाँच' के लिए पैसे ट्रांसफर करने को नहीं कहते।"
        ),
        "decline_known_mule_v1" to LocalTemplate(
            templateId = "decline_known_mule_v1",
            titleEn = "Payment Stopped: High Risk Account",
            titleHi = "भुगतान रोका गया: उच्च जोखिम वाला खाता",
            bodyEn = "This beneficiary has been confirmed as a fraudulent account by bank security analysts.",
            bodyHi = "इस खाते को बैंक सुरक्षा विश्लेषकों द्वारा साइबर धोखाधड़ी के रूप में सत्यापित किया गया है।"
        )
    )

    fun resolve(templateId: String): LocalTemplate {
        return TEMPLATES[templateId] ?: LocalTemplate(
            templateId = templateId,
            titleEn = "Caution: Verify before you pay",
            titleHi = "सावधानी: भुगतान करने से पहले पुष्टि करें",
            bodyEn = "Please review this payment carefully before proceeding.",
            bodyHi = "कृपया आगे बढ़ने से पहले इस भुगतान की सावधानीपूर्वक समीक्षा करें।"
        )
    }
}
