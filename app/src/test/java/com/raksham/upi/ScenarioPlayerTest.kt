package com.raksham.upi

import com.raksham.risk.RiskGate
import com.raksham.risk.model.RiskTier
import com.raksham.upi.simulation.*
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class ScenarioPlayerTest {

    @Test
    fun testScenarioCatalogHasExpectedScenarios() {
        val scenarios = ScenarioCatalog.scenarios
        assertEquals(4, scenarios.size)

        val friendScenario = scenarios.first { it.id == "friend_450" }
        assertEquals(RiskTier.GREEN, friendScenario.expectedTier)
        assertEquals("No interruption", friendScenario.humanExpectedLabel)

        val digitalArrest = scenarios.first { it.id == "digital_arrest" }
        assertEquals(RiskTier.RED, digitalArrest.expectedTier)
        assertEquals("Pause shown", digitalArrest.humanExpectedLabel)
        assertTrue(digitalArrest.signals.on_call)

        val muleCaught = scenarios.first { it.id == "mule_caught" }
        assertEquals(RiskTier.RED, muleCaught.expectedTier)
        assertEquals("Pause shown", muleCaught.humanExpectedLabel)

        val unusualAmount = scenarios.first { it.id == "unusual_amount_no_call" }
        assertEquals(RiskTier.AMBER, unusualAmount.expectedTier)
        assertEquals("Warning shown", unusualAmount.humanExpectedLabel)
    }

    @Test
    fun testScenarioPlayerStepProgression() = runBlocking {
        // Point to offline URL to trigger predictable fallback
        RiskGate.setBaseUrl("http://127.0.0.1:54321")

        val steps = mutableListOf<StepProgress>()
        val unusualScenario = ScenarioCatalog.scenarios.first { it.id == "unusual_amount_no_call" }

        val result = ScenarioPlayer.playScenario(
            scenario = unusualScenario,
            onStepChanged = { steps.add(it) }
        )

        // Verifies step sequence: ENTERING_PAYEE -> CHECKING -> RESULT
        assertEquals(listOf(StepProgress.ENTERING_PAYEE, StepProgress.CHECKING, StepProgress.RESULT), steps)
        assertNotNull(result)
        // With offline backend, RiskGate returns AMBER fallback, matching unusual_amount_no_call's AMBER expectation!
        assertTrue(result.isPassed)
        assertEquals("Warning shown", result.humanResultLabel)
    }
}
