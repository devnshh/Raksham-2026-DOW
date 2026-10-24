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
    /** For the trusted-contact message, in the user's voice: who the user is on a call with, screen
     *  sharing, remote access. */
    val factsForTrustedContact: List<PlainReason> = emptyList(),
    /** For the same message: every other reason, as the app showed it to the user (addressed to "you"). */
    val appWarningsForTrustedContact: List<PlainReason> = emptyList()
)
