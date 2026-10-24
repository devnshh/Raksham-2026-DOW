package com.raksham.upi.simulation

import com.raksham.risk.model.RiskTier
import com.raksham.risk.session.SessionSignals
import com.raksham.upi.ui.components.TrustedContactStatus

enum class ScriptedUserAction {
    NONE,
    HANG_UP_AND_CANCEL,
    CONTINUE_ANYWAY,
    ASK_TRUSTED_CONTACT
}

enum class StepProgress {
    IDLE,
    ENTERING_PAYEE,
    CHECKING,
    RESULT
}

data class DemoScenario(
    val id: String,
    val titleEn: String,
    val titleHi: String,
    val caption: String,
    val userRef: String = "raksham@oksbi",
    val payeeVpa: String,
    val payeeName: String,
    val amount: Double,
    val note: String,
    val entryChannel: String = "typed_vpa",
    val noteIntent: String? = null,
    val linkDomain: String? = null,
    val secsLinkToPay: Double? = null,
    val signals: SessionSignals,
    val expectedTier: RiskTier,
    val humanExpectedLabel: String,
    val trustedContactBehavior: TrustedContactStatus = TrustedContactStatus.IDLE,
    val scriptedAction: ScriptedUserAction = ScriptedUserAction.NONE
)

object ScenarioCatalog {
    val scenarios = listOf(
        DemoScenario(
            id = "friend_450",
            titleEn = "Friend ko ₹450",
            titleHi = "मित्र को ₹450",
            caption = "Legit users feel nothing.",
            payeeVpa = "rahul.sharma@oksbi",
            payeeName = "Rahul Sharma",
            amount = 450.0,
            note = "dinner split",
            signals = SessionSignals(
                on_call = false,
                screen_shared = false,
                remote_app_present = false,
                typing_ms = 280.0,
                pauses = 0,
                pin_secs = 3.2
            ),
            expectedTier = RiskTier.GREEN,
            humanExpectedLabel = "No interruption",
            scriptedAction = ScriptedUserAction.NONE
        ),
        DemoScenario(
            id = "digital_arrest",
            titleEn = "Digital arrest",
            titleHi = "डिजिटल अरेस्ट कॉल",
            caption = "Coerced transfer under active call. Smart pause triggered.",
            payeeVpa = "kyc-helpdesk-update@ybl",
            payeeName = "SBI Quick KYC Support Desk",
            amount = 48000.0,
            note = "cbi verification fee",
            noteIntent = "legal",
            signals = SessionSignals(
                on_call = true,
                screen_shared = false,
                remote_app_present = false,
                app_switches = 3,
                typing_ms = 420.0,
                pauses = 3,
                pin_secs = 8.5
            ),
            expectedTier = RiskTier.RED,
            humanExpectedLabel = "Pause shown",
            trustedContactBehavior = TrustedContactStatus.DECLINED,
            scriptedAction = ScriptedUserAction.HANG_UP_AND_CANCEL
        ),
        DemoScenario(
            id = "mule_caught",
            titleEn = "Mule caught",
            titleHi = "म्यूल खाता पकड़ा गया",
            caption = "18 recent payers + prior complaints trigger mule defense.",
            payeeVpa = "mule.fastcash@okaxis",
            payeeName = "FastCash Payout Mule",
            amount = 25000.0,
            note = "task payout",
            noteIntent = "task",
            signals = SessionSignals(
                on_call = false,
                screen_shared = false,
                remote_app_present = false,
                typing_ms = 310.0,
                pauses = 1,
                pin_secs = 4.0
            ),
            expectedTier = RiskTier.RED,
            humanExpectedLabel = "Pause shown",
            scriptedAction = ScriptedUserAction.HANG_UP_AND_CANCEL
        ),
        DemoScenario(
            id = "unusual_amount_no_call",
            titleEn = "Unusual amount, no call",
            titleHi = "असामान्य राशि, कोई कॉल नहीं",
            caption = "High amount to contact without coercion signals caps at Amber.",
            payeeVpa = "vikram.singh@oksbi",
            payeeName = "Vikram Singh",
            amount = 25000.0,
            note = "advance loan",
            signals = SessionSignals(
                on_call = false,
                screen_shared = false,
                remote_app_present = false,
                typing_ms = 280.0,
                pauses = 0,
                pin_secs = 3.2
            ),
            expectedTier = RiskTier.AMBER,
            humanExpectedLabel = "Warning shown",
            scriptedAction = ScriptedUserAction.CONTINUE_ANYWAY
        )
    )
}
