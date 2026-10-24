package com.raksham.risk

import android.util.Log
import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.model.PlainReason
import com.raksham.risk.model.RiskDecision
import com.raksham.risk.model.RiskTier
import com.raksham.risk.net.PaymentCompletePayload
import com.raksham.risk.net.RiskApiClient
import com.raksham.risk.session.SessionSignalSourceProvider
import com.raksham.risk.session.SessionSignals
import com.raksham.risk.session.SessionTracker
import com.raksham.risk.template.ReasonMapper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
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
        // The blocking HTTP call runs in its own job and the 2000 ms races it: withTimeoutOrNull
        // cannot interrupt HttpURLConnection, so a server sending bytes slowly held the check for
        // over a minute. An abandoned call ends on its own socket timeouts.
        val call = backgroundScope.async {
            try {
                apiClient.assessRisk(payment, signals)
            } catch (e: Exception) {
                null
            }
        }
        val response = withContext(Dispatchers.IO) { withTimeoutOrNull(2000L) { call.await() } }

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
            isCheckUnavailable = isUnavailable,
            sessionUnderPressure = signals.on_call || signals.screen_shared ||
                signals.remote_app_present || signals.remote_app_new,
            factsForTrustedContact = sessionFacts(signals),
            appWarningsForTrustedContact = response.reasons.filter { it.uppercase() !in SESSION_CODES }
                .map { ReasonMapper.mapCodeToPlainReason(it, payment) }
        )
    }

    /** Session reasons are replaced by sessionFacts, which also say who is on the call. */
    private val SESSION_CODES = setOf("ON_CALL", "SCREEN_SHARED", "REMOTE_APP_NEW", "REMOTE_APP_PRESENT", "REMOTE_APP_ACTIVE")

    internal fun sessionFacts(s: SessionSignals): List<PlainReason> = buildList {
        if (s.on_call) add(
            when (s.caller_in_contacts) {
                true -> PlainReason("I am on a call with a saved contact", "मेरी एक सेव किए गए संपर्क से कॉल चल रही है")
                false -> PlainReason("I am on a call with someone who is not in my contacts", "मेरी ऐसे व्यक्ति से कॉल चल रही है जो मेरे संपर्कों में नहीं है")
                null -> PlainReason("I am on a call", "मेरी एक कॉल चल रही है")
            }
        )
        if (s.screen_shared) add(PlainReason("My screen is being shared", "मेरी स्क्रीन शेयर हो रही है"))
        if (s.remote_app_new) add(PlainReason("A remote-access app was installed on my phone today", "आज मेरे फोन पर एक रिमोट-एक्सेस ऐप इंस्टॉल हुआ है"))
        else if (s.remote_app_present) add(PlainReason("A remote-access app is on my phone", "मेरे फोन पर एक रिमोट-एक्सेस ऐप है"))
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

    /** "This was me" on an amber warning: later ambers for this payee are not shown (except during a call).
     *  The server refuses it when this warning itself came during a call or with a remote-access app. */
    suspend fun markThisWasMe(caseId: String): Boolean = dispute(caseId, "appeal")

    /** Red or decline: sends the case to an analyst. Nothing changes for the user until they accept it. */
    suspend fun reportFalseAlarm(caseId: String): Boolean = dispute(caseId, "false-alarm")

    private suspend fun dispute(caseId: String, action: String): Boolean {
        if (caseId.isBlank() || caseId.startsWith("local-offline")) return false
        return try {
            apiClient.dispute(caseId, lastUserRef, action)
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
                .onFailure { Log.w("RiskGate", "Risk API not reachable at warm-up", it) }
        }
    }

    /** Reports the payee as a scam and marks this case cancelled. Runs outside the screen's lifetime, so it
     *  still completes after the warning closes and the user is sent to the dialer or browser. */
    fun reportScamInBackground(caseId: String, payeeVpa: String) {
        val case = caseId.takeUnless { it.isBlank() || it.startsWith("local-offline") }
        backgroundScope.launch { runCatching { apiClient.reportScam(lastUserRef, payeeVpa, case) } }
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
