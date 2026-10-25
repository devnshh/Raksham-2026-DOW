package com.raksham.risk.session

/**
 * Classifies the payment note ON THE PHONE. Only the label leaves the device; the raw note
 * text is never sent to the server. Keep in sync with api/policy/intent.py.
 */
object NoteIntent {
    // Scam stories first: "refund for parents" is a refund note, not rent.
    private val KEYWORDS: List<Pair<String, List<String>>> = listOf(
        "kyc" to listOf("kyc", "verification", "verify"),
        "legal" to listOf("cbi", "police", "legal", "court", "arrest"),
        "investment" to listOf("investment", "profit", "trading", "ipo"),
        "refund" to listOf("refund", "cashback", "rebate"),
        "task" to listOf("task", "commission", "deposit"),
        "receive" to listOf("receive"),
        "food" to listOf("dinner", "food", "lunch", "split"),
        "home" to listOf("rent", "home", "flat"),
        "family" to listOf("family")
    )
    private val WORD = Regex("[a-z0-9]+")

    /** Whole words plus each word without a plural 's' ("parents" is not "rent"). Same rule as intent.py. */
    private fun words(text: String): Set<String> {
        val found = WORD.findAll(text.lowercase()).map { it.value }.toSet()
        return found + found.filter { it.length > 3 && it.endsWith("s") }.map { it.dropLast(1) }
    }

    fun classify(note: String?): String {
        if (note.isNullOrBlank()) return "none"
        val found = words(note)
        return KEYWORDS.firstOrNull { (_, keywords) -> keywords.any { it in found } }?.first ?: "none"
    }
}
