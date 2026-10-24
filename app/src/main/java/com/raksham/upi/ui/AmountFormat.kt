package com.raksham.upi.ui

/** Indian digit grouping, as UPI apps show amounts: 48000 becomes 48,000 and 1234567 becomes 12,34,567. */
fun groupIndian(digits: String): String {
    if (digits.length <= 3) return digits
    val head = digits.dropLast(3).reversed().chunked(2).joinToString(",").reversed()
    return "$head,${digits.takeLast(3)}"
}

/** Amount without the rupee sign, Indian grouping, paise only when there are any (450, 1,250.50). */
fun formatAmount(amount: Double): String {
    val paiseTotal = Math.round(amount * 100)
    val whole = groupIndian((paiseTotal / 100).toString())
    val paise = paiseTotal % 100
    return if (paise == 0L) whole else "$whole.${paise.toString().padStart(2, '0')}"
}
