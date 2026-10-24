package com.raksham.upi.ui.components

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CallEnd
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.ReportProblem
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.raksham.risk.RiskGate
import com.raksham.risk.model.RiskDecision
import com.raksham.upi.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun RedSmartPauseDialog(
    decision: RiskDecision,
    payeeVpa: String,
    amount: Double,
    onHangUpAndCancel: () -> Unit,
    onAskTrustedContact: () -> Unit,
    onProceedAfterHold: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var showTrustedContactSheet by remember { mutableStateOf(false) }
    var showReportSheet by remember { mutableStateOf(false) }
    var showFinalReleaseWarning by remember { mutableStateOf(false) }

    // Questionnaire check state
    var selectedQuestionnaireAnswer by remember { mutableStateOf<String?>(null) }
    var questionnaireSubmitted by remember { mutableStateOf(false) }

    // Hold Timer initialized once with decision.holdMinutes
    LaunchedEffect(decision.holdMinutes) {
        val durationMins = if (decision.holdMinutes > 0) decision.holdMinutes else 30
        HoldTimerManager.startHold(durationMins)
    }

    // Ticking state for live countdown display
    var remainingSeconds by remember { mutableIntStateOf(HoldTimerManager.getRemainingSeconds()) }

    LaunchedEffect(Unit) {
        while (true) {
            remainingSeconds = HoldTimerManager.getRemainingSeconds()
            if (remainingSeconds <= 0) break
            delay(1000L)
        }
    }

    val isHoldComplete = remainingSeconds <= 0
    val timeFormatted = HoldTimerManager.formatRemainingTime()

    // Unskippable by back button (back = Hang up and cancel)
    BackHandler {
        onHangUpAndCancel()
    }

    Dialog(
        onDismissRequest = { onHangUpAndCancel() },
        properties = DialogProperties(
            dismissOnBackPress = false,
            dismissOnClickOutside = false,
            usePlatformDefaultWidth = false
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFFB3261E)) // Full-screen Red Tier Accent
        ) {
            Surface(
                modifier = Modifier
                    .fillMaxSize()
                    .systemBarsPadding(),
                color = Color.White
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 20.dp, vertical = 12.dp)
                        .verticalScroll(rememberScrollState()),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Spacer(modifier = Modifier.height(8.dp))

                    // Red Alert Icon
                    Box(
                        modifier = Modifier
                            .size(68.dp)
                            .background(Color(0xFFFCE8E6), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = "Security Alert",
                            tint = GPayRed,
                            modifier = Modifier.size(40.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // 1. Headline
                    Text(
                        text = "Wait. This looks like a scam call.",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = GPayRed,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.semantics { heading() }
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    // 2. Fact-Based Body from reasons, amount, and payee
                    val formattedAmount = String.format("%,.0f", amount)
                    val factBodyEn = buildString {
                        append("You are attempting to transfer ₹$formattedAmount to $payeeVpa. ")
                        if (decision.reasons.isNotEmpty()) {
                            append("Our safety systems detected: ")
                            append(decision.reasons.joinToString(", ") { it.en })
                            append(". ")
                        }
                        append("Legitimate officials and banks will NEVER ask you to make urgent payments or move funds to a 'safe account'.")
                    }

                    Text(
                        text = factBodyEn,
                        fontSize = 16.sp,
                        color = TextPrimary,
                        lineHeight = 22.sp,
                        textAlign = TextAlign.Start,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    // 3. Official Warning Box (English + Hindi)
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFFEF7E0),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Text(
                                text = "पुलिस या बैंक कभी \"जाँच\" के लिए पैसे ट्रांसफर करने को नहीं कहते।",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF7A4B04)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "Police and banks never ask you to move money \"for verification\".",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color(0xFF7A4B04)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // 4. Interactive Questionnaire: "Is someone on the phone telling you what to do?"
                    Surface(
                        shape = RoundedCornerShape(14.dp),
                        color = SurfaceBackground,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Text(
                                text = "Quick Check: Is someone on the phone telling you what to do?",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Text(
                                text = "क्या फोन पर कोई आपको निर्देश दे रहा है?",
                                fontSize = 13.sp,
                                color = TextMuted
                            )

                            Spacer(modifier = Modifier.height(10.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                listOf("Yes", "No", "Not sure").forEach { option ->
                                    val isSelected = selectedQuestionnaireAnswer == option
                                    Surface(
                                        shape = RoundedCornerShape(10.dp),
                                        color = if (isSelected) GPayBlueLight else Color.White,
                                        border = if (isSelected) ButtonDefaults.outlinedButtonBorder else null,
                                        modifier = Modifier
                                            .weight(1f)
                                            .height(44.dp)
                                            .clip(RoundedCornerShape(10.dp))
                                            .clickable {
                                                selectedQuestionnaireAnswer = option
                                                if (!questionnaireSubmitted) {
                                                    questionnaireSubmitted = true
                                                    coroutineScope.launch {
                                                        val isGuiding = (option == "Yes")
                                                        RiskGate.sendQuestionnaireAnswer(decision.caseId, isGuiding)
                                                    }
                                                }
                                            }
                                    ) {
                                        Box(contentAlignment = Alignment.Center) {
                                            Text(
                                                text = option,
                                                fontSize = 14.sp,
                                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                                color = if (isSelected) GPayBlue else TextPrimary
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // 5. Action 1: Hang up and cancel (Primary)
                    Button(
                        onClick = onHangUpAndCancel,
                        colors = ButtonDefaults.buttonColors(containerColor = GPayRed),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                            .semantics { contentDescription = "Hang up call and cancel payment" }
                    ) {
                        Icon(Icons.Default.CallEnd, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Hang Up & Cancel Payment",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // 6. Action 2: Ask my trusted contact
                    OutlinedButton(
                        onClick = { showTrustedContactSheet = true },
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                            .semantics { contentDescription = "Ask trusted contact for advice" }
                    ) {
                        Icon(Icons.Default.People, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Ask My Trusted Contact",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // 7. Action 3: Continue after hold (Disabled countdown surviving rotation)
                    Button(
                        onClick = {
                            if (isHoldComplete) {
                                showFinalReleaseWarning = true
                            }
                        },
                        enabled = isHoldComplete,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isHoldComplete) GPayBlue else Color(0xFFE0E2EC),
                            disabledContainerColor = Color(0xFFF1F3F9),
                            disabledContentColor = TextMuted
                        ),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                            .semantics {
                                liveRegion = LiveRegionMode.Polite
                                contentDescription = if (isHoldComplete) {
                                    "Continue after safety hold ended"
                                } else {
                                    "Continue disabled, safety hold active: $timeFormatted remaining"
                                }
                            }
                    ) {
                        Icon(
                            imageVector = if (isHoldComplete) Icons.Default.Lock else Icons.Default.HourglassTop,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (isHoldComplete) {
                                "Continue to PIN (Hold Ended)"
                            } else {
                                "Continue after $timeFormatted"
                            },
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // 8. "Report a scam" row -> opens 1930 flow
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .clickable { showReportSheet = true }
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Security,
                            contentDescription = null,
                            tint = TextSecondary,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Report a scam (Call 1930 / cybercrime.gov.in)",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Medium,
                            color = TextSecondary
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))
                }
            }

            // Sheet 1: Ask Trusted Contact Sheet
            if (showTrustedContactSheet) {
                TrustedContactSheet(
                    contactFirstName = "Aarav",
                    payeeName = payeeVpa,
                    amount = amount,
                    onDismiss = { showTrustedContactSheet = false },
                    onDeclined = {
                        showTrustedContactSheet = false
                        onHangUpAndCancel()
                    },
                    onApproved = {
                        showTrustedContactSheet = false
                    }
                )
            }

            // Sheet 2: 1930 / Cybercrime Reporting Sheet
            if (showReportSheet) {
                ReportScamSheet(
                    payeeVpa = payeeVpa,
                    amount = amount,
                    reasons = decision.reasons,
                    caseId = decision.caseId,
                    onDismiss = { showReportSheet = false }
                )
            }

            // Release-after-hold: Final warning dialog before PIN screen
            if (showFinalReleaseWarning) {
                AlertDialog(
                    onDismissRequest = { showFinalReleaseWarning = false },
                    title = {
                        Text(
                            text = "Final Caution Notice",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = GPayRed
                        )
                    },
                    text = {
                        Text(
                            text = "The 30-minute safety pause has elapsed. If anyone is coaching you on the phone, hang up now. Once the PIN is entered, funds cannot be reversed.",
                            fontSize = 15.sp,
                            lineHeight = 21.sp
                        )
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                showFinalReleaseWarning = false
                                onProceedAfterHold()
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = GPayRed)
                        ) {
                            Text("I understand, enter PIN")
                        }
                    },
                    dismissButton = {
                        OutlinedButton(onClick = { showFinalReleaseWarning = false }) {
                            Text("Back to safety")
                        }
                    }
                )
            }
        }
    }
}
