package com.raksham.risk.session

import kotlinx.serialization.Serializable

/**
 * Derived session signals sent to the Risk API. Values the phone could not measure are null
 * ("no evidence"), never an invented default. pin_secs is null at risk-check time because the
 * check runs before the PIN screen; it is only sent with the payment-complete call.
 */
@Serializable
data class SessionSignals(
    val on_call: Boolean = false,
    /** On a call with a contact saved at least 7 days ago; null = not measured (see CallerCheck). */
    val caller_in_contacts: Boolean? = null,
    val screen_shared: Boolean = false,
    val remote_app_present: Boolean = false,
    val remote_app_new: Boolean = false,
    val app_switches: Int = 0,
    val typing_ms: Double? = null,
    val pauses: Int? = null,
    val pin_secs: Double? = null,
    val device_new: Boolean = false,
    val failed_auth: Int = 0
)
