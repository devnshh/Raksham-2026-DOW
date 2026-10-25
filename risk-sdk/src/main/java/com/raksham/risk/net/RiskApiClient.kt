package com.raksham.risk.net

import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.session.NoteIntent
import com.raksham.risk.session.SessionSignals
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.UUID

@Serializable
internal data class AssessmentNetworkRequest(
    val txn_ref: String? = null,
    val user_ref: String? = null,
    val payee_vpa: String,
    val amount: Double,
    val entry_channel: String = "typed_vpa",
    val session: SessionSignals,
    val context: ContextPayload = ContextPayload()
)

/** Only the note's intent label is sent; the raw note text never leaves the phone. */
@Serializable
internal data class ContextPayload(
    val note_intent: String? = null,
    val link_domain: String? = null,
    val secs_link_to_pay: Double? = null
)

@Serializable
internal data class AssessmentNetworkResponse(
    val tier: String,
    val reasons: List<String> = emptyList(),
    val template_id: String = "default",
    val hold_minutes: Int = 0,
    val case_id: String = ""
)

@Serializable
internal data class QuestionnairePayload(
    val user_ref: String,
    val answers: Map<String, Boolean>
)

@Serializable
internal data class AppealPayload(val user_ref: String)

/** A red pause's hold as the server sees it (POST /v1/risk/{case_id}/status). */
@Serializable
data class CaseStatus(
    val case_id: String = "",
    val tier: String = "",
    val hold_active: Boolean = true,
    val hold_seconds_left: Int = 0,
    val released: Boolean = false,
    val status: String = "open"
)

@Serializable
internal data class ReportPayload(
    val reporter_id: String,
    val payee_vpa: String,
    val reason: String,
    val case_id: String? = null
)

@Serializable
internal data class PaymentCompletePayload(
    val case_id: String,
    val user_ref: String,
    val payee_vpa: String,
    val amount: Double,
    val typing_ms: Double? = null,
    val pauses: Int? = null,
    val pin_secs: Double? = null
)

internal class RiskApiClient(
    var baseUrl: String = "http://10.0.2.2:8000"
) {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    private fun post(path: String, body: String, connectMs: Int, readMs: Int): Pair<Int, String> {
        val conn = (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = connectMs
            readTimeout = readMs
            doInput = true
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        try {
            OutputStreamWriter(conn.outputStream, "UTF-8").use { it.write(body) }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else (conn.errorStream ?: conn.inputStream)
            val text = try {
                BufferedReader(InputStreamReader(stream, "UTF-8")).use { it.readText() }
            } catch (e: Exception) {
                ""
            }
            return code to text
        } finally {
            conn.disconnect()
        }
    }

    /**
     * Loads the HTTP stack and JSON serializers once, off the payment path. Without it the first
     * check after launch spends about a second on class loading and can miss the time budget.
     */
    fun warmUp() {
        json.encodeToString(AssessmentNetworkRequest(payee_vpa = "", amount = 0.0, session = SessionSignals()))
        json.decodeFromString<AssessmentNetworkResponse>("""{"tier":"green"}""")
        val conn = URL(baseUrl.trimEnd('/') + "/health").openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 2000
            conn.readTimeout = 2000
            conn.inputStream.use { it.readBytes() }
        } finally {
            conn.disconnect()
        }
    }

    suspend fun assessRisk(
        payment: PaymentRequest,
        signals: SessionSignals
    ): AssessmentNetworkResponse = withContext(Dispatchers.IO) {
        val payload = AssessmentNetworkRequest(
            txn_ref = "t-${UUID.randomUUID().toString().take(8)}",
            user_ref = payment.userRef,
            payee_vpa = payment.payeeVpa,
            amount = payment.amount,
            entry_channel = payment.entryChannel,
            session = signals,
            context = ContextPayload(
                note_intent = payment.noteIntent ?: NoteIntent.classify(payment.noteText),
                link_domain = payment.linkDomain,
                secs_link_to_pay = payment.secsLinkToPay
            )
        )
        val (code, text) = post("/v1/risk/assess", json.encodeToString(payload), 1000, 2000)
        if (code !in 200..299) throw RuntimeException("Risk API returned HTTP $code: $text")
        json.decodeFromString<AssessmentNetworkResponse>(text)
    }

    /** Attaches the red-tier answer to the SAME case; the server can only raise the tier. */
    suspend fun sendQuestionnaireAnswer(
        caseId: String,
        userRef: String,
        isAnyoneGuidingYou: Boolean
    ): AssessmentNetworkResponse? = withContext(Dispatchers.IO) {
        val path = "/v1/risk/${URLEncoder.encode(caseId, "UTF-8")}/questionnaire"
        val body = json.encodeToString(
            QuestionnairePayload(userRef, mapOf("is_anyone_guiding_you" to isAnyoneGuidingYou))
        )
        val (code, text) = post(path, body, 800, 800)
        if (code in 200..299) json.decodeFromString<AssessmentNetworkResponse>(text) else null
    }

    /** Scam report on a payee; with the case it came from, the server marks that case cancelled. */
    suspend fun reportScam(userRef: String, payeeVpa: String, caseId: String?): Boolean = withContext(Dispatchers.IO) {
        val body = json.encodeToString(ReportPayload(userRef, payeeVpa, "Reported from a warning in the app", caseId))
        val (code, _) = post("/v1/report", body, 800, 800)
        code in 200..299
    }

    /** "This was me" (amber), "Report a false alarm" (red, decline) or a cancel: action is "appeal", "false-alarm" or "cancel". */
    suspend fun dispute(caseId: String, userRef: String, action: String): Boolean = withContext(Dispatchers.IO) {
        val path = "/v1/risk/${URLEncoder.encode(caseId, "UTF-8")}/$action"
        val (code, _) = post(path, json.encodeToString(AppealPayload(userRef)), 800, 800)
        code in 200..299
    }

    /** The server's view of a case's hold; null if it could not be read. */
    suspend fun caseStatus(caseId: String, userRef: String): CaseStatus? = withContext(Dispatchers.IO) {
        val path = "/v1/risk/${URLEncoder.encode(caseId, "UTF-8")}/status"
        val (code, text) = post(path, json.encodeToString(AppealPayload(userRef)), 800, 800)
        if (code in 200..299) json.decodeFromString<CaseStatus>(text) else null
    }

    /** Tells the server the PIN succeeded, so the payment updates baselines and fan-in. */
    suspend fun completePayment(payload: PaymentCompletePayload): Boolean = withContext(Dispatchers.IO) {
        val (code, _) = post("/v1/payments/complete", json.encodeToString(payload), 800, 800)
        code in 200..299
    }
}
