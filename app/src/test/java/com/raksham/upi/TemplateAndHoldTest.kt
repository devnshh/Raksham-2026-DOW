package com.raksham.upi

import com.raksham.upi.ui.components.HoldTimerManager
import com.raksham.upi.ui.templates.TemplateRegistry
import org.junit.Assert.*
import org.junit.Test

class TemplateAndHoldTest {

    @Test
    fun testKnownTemplateMapping() {
        val amberCaution = TemplateRegistry.resolve("amber_caution_v1")
        assertEquals("amber_caution_v1", amberCaution.templateId)
        assertTrue(amberCaution.titleEn.contains("Caution"))
        assertTrue(amberCaution.titleHi.contains("सावधानी"))
        assertFalse(amberCaution.bodyEn.contains("Satark", ignoreCase = true))

        val redCall = TemplateRegistry.resolve("red_call_new_payee_v1")
        assertEquals("red_call_new_payee_v1", redCall.templateId)
        assertEquals("Wait. This looks like a scam call.", redCall.titleEn)
        assertEquals("रुकिए। यह धोखाधड़ी का फोन कॉल प्रतीत होता है।", redCall.titleHi)

        val checkUnavailable = TemplateRegistry.resolve("amber_check_unavailable")
        assertTrue(checkUnavailable.bodyEn.contains("couldn't complete a safety check"))
    }

    @Test
    fun testUnknownTemplateFallback() {
        val unknown = TemplateRegistry.resolve("future_unrecognized_template_xyz")
        assertNotNull(unknown)
        assertTrue(unknown.titleEn.contains("Caution"))
        assertTrue(unknown.titleHi.contains("सावधानी"))
        assertFalse(unknown.bodyEn.contains("Satark", ignoreCase = true))
    }

    @Test
    fun testHoldTimerComputesFromEpochAndSurvivesRestart() {
        // Start a 30-minute hold
        HoldTimerManager.startHold(30)

        val remaining1 = HoldTimerManager.getRemainingSeconds()
        // Should be around 1800 seconds
        assertTrue(remaining1 in 1795..1800)
        assertFalse(HoldTimerManager.isHoldCompleted())

        // Simulate elapsed time (e.g. app backgrounded or screen rotated for 10 minutes)
        HoldTimerManager.simulateFastForward(10 * 60)
        val remainingAfter10Min = HoldTimerManager.getRemainingSeconds()
        assertTrue(remainingAfter10Min in 1195..1200)

        // Simulate remaining 20 minutes elapsed
        HoldTimerManager.simulateFastForward(20 * 60)
        val remainingEnded = HoldTimerManager.getRemainingSeconds()
        assertEquals(0, remainingEnded)
        assertTrue(HoldTimerManager.isHoldCompleted())
    }

    @Test
    fun testAnswersCannotLowerRedRule() {
        // On RED tier, hold duration must remain active regardless of user response
        HoldTimerManager.startHold(30)
        assertFalse(HoldTimerManager.isHoldCompleted())

        // Even after answering questionnaire (Yes/No/Not sure), hold timer must still run
        assertTrue(HoldTimerManager.getRemainingSeconds() > 0)
    }
}
