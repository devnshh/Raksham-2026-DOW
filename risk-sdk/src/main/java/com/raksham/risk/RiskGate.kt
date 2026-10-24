package com.raksham.risk

import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.model.PlainReason
import com.raksham.risk.model.RiskDecision
import com.raksham.risk.model.RiskTier
import com.raksham.risk.net.PaymentCompletePayload
import com.raksham.risk.net.RiskApiClient
import com.raksham.risk.session.SessionSignalSourceProvider
import com.raksham.risk.session.SessionTracker
import com.raksham.risk.template.ReasonMapper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

object RiskGate {
    private var apiClient: RiskApiClient = RiskApiClient()

    /** User of the most recent check; the questionnaire answer must come from the same user. */
    private var lastUserRef: String = ""

    fun setBaseUrl(url: String) {
        apiClient = RiskApiClient(baseUrl = url)
    }

    fun getBaseUrl(): String = apiClient.baseUrl

    suspend fun check(payment: PaymentRequest): RiskDecision {
        val signals = SessionSignalSourceProvider.current.collectSignals()
        lastUserRef = payment.userRef

        // 2000 ms client timeout - maps timeout or exception to CHECK_UNAVAILABLE amber. The first
        // check after launch pays class loading and JSON setup; 600 ms missed it on slow phones.
        // Timed on the IO thread: on the caller's (main) thread a janky frame would count
        // against the budget and turn a fast answer into CHECK_UNAVAILABLE.
        val response = withContext(Dispatchers.IO) {
            withTimeoutOrNull(2000L) {
                try {
                    apiClient.assessRisk(payment, signals)
                } catch (e: Exception) {
                    null
                }
            }
        }

        if (response == null) {
            return fallbackUnavailableDecision(payment)
        }

        val tier = when (response.tier.lowercase()) {
            "decline" -> RiskTier.DECLINE
            "red" -> RiskTier.RED
            "amber" -> RiskTier.AMBER
            else -> RiskTier.GREEN
        }

        val plainReasons = response.reasons.map { code ->
            ReasonMapper.mapCodeToPlainReason(code, payment)
        }

        val isUnavailable = response.reasons.any { it.contains("UNAVAILABLE", ignoreCase = true) }

        return RiskDecision(
            tier = tier,
            reasons = plainReasons,
            templateId = response.template_id,
            holdMinutes = response.hold_minutes,
            caseId = response.case_id,
            isCheckUnavailable = isUnavailable
        )
    }

    /** Sends the red-tier answer for this case. Returns false if it could not be delivered. */
    suspend fun sendQuestionnaireAnswer(caseId: String, isAnyoneGuidingYou: Boolean): Boolean {
        if (caseId.startsWith("local-offline")) return false
        return try {
            apiClient.sendQuestionnaireAnswer(caseId, lastUserRef, isAnyoneGuidingYou) != null
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Call after the PIN succeeds. Only completed payments update the user's baseline and the
     * payee's fan-in on the server. Best effort: a failure here never blocks the payment UI.
     */
    suspend fun reportPaymentCompleted(caseId: String, payment: PaymentRequest, pinSecs: Double?): Boolean {
        if (caseId.isBlank() || caseId.startsWith("local-offline")) return false
        return try {
            apiClient.completePayment(
                PaymentCompletePayload(
                    case_id = caseId,
                    user_ref = payment.userRef,
                    payee_vpa = payment.payeeVpa,
                    amount = payment.amount,
                    typing_ms = SessionTracker.typingMs(),
                    pauses = SessionTracker.pauses(),
                    pin_secs = pinSecs
                )
            )
        } catch (e: Exception) {
            false
        }
    }

    /** Not tied to any screen, so the call survives navigating to the success screen. */
    private val backgroundScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** Call at app start and after changing the API address. Best effort, never blocks. */
    fun warmUp() {
        backgroundScope.launch {
            runCatching { SessionSignalSourceProvider.current.collectSignals() }
            runCatching { apiClient.warmUp() }
        }
    }

    /** Fire-and-forget version of [reportPaymentCompleted] for UI callbacks. */
    fun reportPaymentCompletedInBackground(caseId: String, payment: PaymentRequest, pinSecs: Double?) {
        backgroundScope.launch { reportPaymentCompleted(caseId, payment, pinSecs) }
    }

    private fun fallbackUnavailableDecision(payment: PaymentRequest): RiskDecision {
        return RiskDecision(
            tier = RiskTier.AMBER,
            reasons = listOf(
                PlainReason(
                    en = "We couldn't complete a safety check. Please confirm this payee before continuing.",
                    hi = "हम सुरक्षा जांच पूरी नहीं कर सके। कृपया जारी रखने से पहले इस प्राप्तकर्ता की पुष्टि करें।"
                )
            ),
            templateId = "amber_check_unavailable",
            holdMinutes = 0,
            caseId = "local-offline-${System.currentTimeMillis()}",
            isCheckUnavailable = true
        )
    }
}
