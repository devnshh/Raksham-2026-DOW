package com.raksham.upi.simulation

import com.raksham.risk.RiskGate
import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.model.RiskDecision
import com.raksham.risk.model.RiskTier
import com.raksham.risk.session.ScriptedSignalSource
import com.raksham.risk.session.SessionSignalSourceProvider
import com.raksham.upi.ui.components.SimulatedTrustedContactController
import com.raksham.upi.ui.screens.PaymentScreenController
import kotlinx.coroutines.delay

data class ScenarioExecutionResult(
    val scenarioId: String,
    val isPassed: Boolean,
    val actualTier: RiskTier,
    val humanResultLabel: String,
    val message: String = ""
)

object ScenarioPlayer {

    suspend fun playScenario(
        scenario: DemoScenario,
        onStepChanged: (StepProgress) -> Unit = {},
        onTypingProgress: (amount: String, note: String) -> Unit = { _, _ -> }
    ): ScenarioExecutionResult {
        // 1. Swap in ScriptedSignalSource for the run
        val scriptedSignals = ScriptedSignalSource(scenario.signals)
        SessionSignalSourceProvider.setScriptedSource(scriptedSignals)
        SimulatedTrustedContactController.scriptedOutcome = scenario.trustedContactBehavior

        try {
            // Step 1: Entering Payee & Typing Animation
            onStepChanged(StepProgress.ENTERING_PAYEE)
            val fullAmountStr = String.format("%.0f", scenario.amount)
            val fullNote = scenario.note

            // Visible typing animation
            var currentAmt = ""
            for (char in fullAmountStr) {
                currentAmt += char
                PaymentScreenController.programmaticAmount = currentAmt
                onTypingProgress(currentAmt, "")
                delay(60L)
            }

            var currentNote = ""
            for (char in fullNote) {
                currentNote += char
                PaymentScreenController.programmaticNote = currentNote
                onTypingProgress(currentAmt, currentNote)
                delay(30L)
            }

            delay(200L)

            // Step 2: Checking Risk with port 8000 backend
            onStepChanged(StepProgress.CHECKING)

            val paymentRequest = PaymentRequest(
                payeeVpa = scenario.payeeVpa,
                amount = scenario.amount,
                payeeDisplayName = scenario.payeeName,
                noteText = scenario.note,
                entryChannel = scenario.entryChannel,
                userRef = scenario.userRef,
                noteIntent = scenario.noteIntent,
                linkDomain = scenario.linkDomain,
                secsLinkToPay = scenario.secsLinkToPay
            )

            val decision: RiskDecision = RiskGate.check(paymentRequest)

            // Step 3: Result
            onStepChanged(StepProgress.RESULT)
            delay(300L)

            val isPassed = (decision.tier == scenario.expectedTier)
            val humanResult = when (decision.tier) {
                RiskTier.GREEN -> "No interruption"
                RiskTier.AMBER -> "Warning shown"
                RiskTier.RED -> "Pause shown"
                RiskTier.DECLINE -> "Payment blocked"
            }

            return ScenarioExecutionResult(
                scenarioId = scenario.id,
                isPassed = isPassed,
                actualTier = decision.tier,
                humanResultLabel = humanResult,
                message = if (isPassed) "Outcome matched expected behavior" else "Expected ${scenario.humanExpectedLabel} but got $humanResult"
            )
        } finally {
            // Restore RealSignalSource afterwards
            SessionSignalSourceProvider.restoreRealSource()
        }
    }
}
