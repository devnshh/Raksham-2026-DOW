package com.raksham.risk

import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.model.RiskTier
import com.raksham.risk.session.ScriptedSignalSource
import com.raksham.risk.session.SessionSignals
import com.raksham.risk.session.SessionSignalSourceProvider
import com.raksham.risk.template.ReasonMapper
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class RiskGateTest {

    @Before
    fun setup() {
        SessionSignalSourceProvider.restoreRealSource()
    }

    @Test
    fun testReasonCodeMappingKnown() {
        val mappedOnCall = ReasonMapper.mapCodeToPlainReason("ON_CALL")
        assertEquals("Active phone call detected during payment", mappedOnCall.en)
        assertTrue(mappedOnCall.hi.contains("फोन कॉल"))

        val mappedLookalike = ReasonMapper.mapCodeToPlainReason("LOOKALIKE_HANDLE")
        assertEquals("UPI handle mimics a known organization or brand", mappedLookalike.en)
        assertTrue(mappedLookalike.hi.contains("यूपीआई आईडी"))

        val mappedReports = ReasonMapper.mapCodeToPlainReason("REPORTED_BY_OTHERS")
        assertEquals("Beneficiary has previous scam complaints reported", mappedReports.en)
        assertTrue(mappedReports.hi.contains("धोखाधड़ी"))
    }

    @Test
    fun testReasonCodeMappingUnknownFallback() {
        val mapped = ReasonMapper.mapCodeToPlainReason("NON_EXISTENT_FUTURE_CODE")
        assertEquals("Unusual payment activity detected.", mapped.en)
        assertEquals("असामान्य भुगतान गतिविधि का पता चला।", mapped.hi)
    }

    @Test
    fun testTimeoutOrOfflineFallsBackToAmberCheckUnavailable() = runBlocking {
        // Point to an invalid unreachable port to test offline / timeout fallback
        RiskGate.setBaseUrl("http://127.0.0.1:54321")

        val payment = PaymentRequest(
            payeeVpa = "some.payee@oksbi",
            amount = 1500.0
        )

        val decision = RiskGate.check(payment)

        // Must never fail open to GREEN on network failure or timeout
        assertEquals(RiskTier.AMBER, decision.tier)
        assertTrue(decision.isCheckUnavailable)
        assertEquals(0, decision.holdMinutes)
        assertTrue(decision.reasons.isNotEmpty())
        assertTrue(decision.reasons.first().en.contains("couldn't complete a safety check"))
    }

    @Test
    fun testSlowServerStillAnswersWithinTwoSeconds() = runBlocking {
        // A server that sends the response one byte every 400 ms: each read succeeds, so the socket
        // read timeout never fires. The check must still give up at about 2 seconds.
        val server = java.net.ServerSocket(0)
        val drip = Thread {
            runCatching {
                server.accept().use { s ->
                    s.getInputStream().read(ByteArray(4096))
                    val out = s.getOutputStream()
                    out.write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 200\r\n\r\n".toByteArray())
                    repeat(200) { out.write('{'.code); out.flush(); Thread.sleep(400) }
                }
            }
        }.apply { isDaemon = true; start() }
        RiskGate.setBaseUrl("http://127.0.0.1:${server.localPort}")

        val started = System.currentTimeMillis()
        val decision = RiskGate.check(PaymentRequest(payeeVpa = "some.payee@oksbi", amount = 1500.0))
        val took = System.currentTimeMillis() - started

        assertEquals(RiskTier.AMBER, decision.tier)
        assertTrue(decision.isCheckUnavailable)
        assertTrue("check took $took ms", took < 3000)
        server.close(); drip.interrupt()
    }

    @Test
    fun testScriptedSignalSourceSwapping() {
        val scripted = ScriptedSignalSource(
            SessionSignals(on_call = true, screen_shared = true, app_switches = 5)
        )
        SessionSignalSourceProvider.setScriptedSource(scripted)

        val currentSignals = SessionSignalSourceProvider.current.collectSignals()
        assertTrue(currentSignals.on_call)
        assertTrue(currentSignals.screen_shared)
        assertEquals(5, currentSignals.app_switches)

        SessionSignalSourceProvider.restoreRealSource()
        val restoredSignals = SessionSignalSourceProvider.current.collectSignals()
        // Restored real source has default/detected values
        assertNotNull(restoredSignals)
    }
}
