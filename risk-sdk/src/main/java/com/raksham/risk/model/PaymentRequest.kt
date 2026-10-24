package com.raksham.risk.model

data class PaymentRequest(
    val payeeVpa: String,
    val amount: Double,
    val payeeDisplayName: String = "",
    val noteText: String = "",
    val entryChannel: String = "typed_vpa",
    val userRef: String = "raksham@oksbi",
    val noteIntent: String? = null,
    val linkDomain: String? = null,
    val secsLinkToPay: Double? = null
)
