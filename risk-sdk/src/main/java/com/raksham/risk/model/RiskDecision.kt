package com.raksham.risk.model

data class RiskDecision(
    val tier: RiskTier,
    val reasons: List<PlainReason>,
    val templateId: String,
    val holdMinutes: Int,
    val caseId: String,
    val isCheckUnavailable: Boolean = false,
    /** A call, screen share or remote-access app was active: "This was me" is not offered (or accepted). */
    val sessionUnderPressure: Boolean = false,
    /** Everything worrying about this payment, in the user's voice, for the trusted-contact message:
     *  who the user is on a call with, screen sharing, remote access, then every reason found. */
    val factsForTrustedContact: List<PlainReason> = emptyList()
)
