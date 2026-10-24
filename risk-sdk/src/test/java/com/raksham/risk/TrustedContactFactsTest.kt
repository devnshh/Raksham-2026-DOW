package com.raksham.risk

import com.raksham.risk.session.SessionSignals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The trusted-contact message must say who the user is on a call with and what else is happening. */
class TrustedContactFactsTest {

    @Test
    fun unknownCallerScreenShareAndNewRemoteAppAreAllStated() {
        val facts = RiskGate.sessionFacts(
            SessionSignals(on_call = true, caller_in_contacts = false, screen_shared = true,
                remote_app_present = true, remote_app_new = true)
        ).map { it.en }
        assertEquals(3, facts.size)
        assertTrue(facts[0].contains("not in my contacts"))
        assertTrue(facts.any { it.contains("screen is being shared") })
        assertTrue(facts.any { it.contains("installed on my phone today") })
    }

    @Test
    fun aSavedContactCallIsDescribedAsSuch() {
        val facts = RiskGate.sessionFacts(SessionSignals(on_call = true, caller_in_contacts = true)).map { it.en }
        assertEquals(listOf("I am on a call with a saved contact"), facts)
    }

    @Test
    fun nothingHappeningMeansNoSessionFacts() {
        assertTrue(RiskGate.sessionFacts(SessionSignals()).isEmpty())
    }
}
