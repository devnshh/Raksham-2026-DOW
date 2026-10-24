package com.raksham.risk.model

data class RiskDecision(
    val tier: RiskTier,
    val reasons: List<PlainReason>,
    val templateId: String,
    val holdMinutes: Int,
    val caseId: String,
    val isCheckUnavailable: Boolean = false,
    /** A call, screen share or remote-access app was active: "This was me" is not offered (or accepted). */
    val sessionUnderPressure: Boolean = false
)
