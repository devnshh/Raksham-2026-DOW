package com.raksham.risk.model

enum class RiskTier {
    GREEN,
    AMBER,
    RED,

    /** Analyst-confirmed scam payee: the payment must not proceed (no "continue" path). */
    DECLINE
}
