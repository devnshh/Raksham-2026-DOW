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
