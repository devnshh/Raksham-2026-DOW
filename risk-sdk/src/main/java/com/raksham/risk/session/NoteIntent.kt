package com.raksham.risk.session

/**
 * Classifies the payment note ON THE PHONE. Only the label leaves the device; the raw note
 * text is never sent to the server. Keep in sync with api/policy/intent.py.
 */
object NoteIntent {
    private val KEYWORDS: List<Pair<String, List<String>>> = listOf(
        "kyc" to listOf("kyc", "verification", "verify"),
        "food" to listOf("dinner", "food", "lunch", "split"),
        "home" to listOf("rent", "home", "flat"),
        "legal" to listOf("cbi", "police", "legal", "court", "arrest"),
        "investment" to listOf("investment", "profit", "trading", "ipo"),
        "refund" to listOf("refund", "cashback", "rebate"),
        "task" to listOf("task", "commission", "deposit"),
        "receive" to listOf("receive"),
        "family" to listOf("family")
    )

    fun classify(note: String?): String {
        val text = note?.lowercase().orEmpty()
        if (text.isBlank()) return "none"
        return KEYWORDS.firstOrNull { (_, words) -> words.any { text.contains(it) } }?.first ?: "none"
    }
}
