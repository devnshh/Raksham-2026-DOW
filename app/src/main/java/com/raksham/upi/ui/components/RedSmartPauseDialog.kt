package com.raksham.upi.ui.components

import com.raksham.upi.ui.formatAmount
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.ZeroCornerSize
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CallEnd
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.raksham.risk.RiskGate
import com.raksham.risk.model.RiskDecision
import com.raksham.upi.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Rise 16dp into place; `index` staggers sections by 55 ms (whole entrance stays under 600 ms).
 * Text starts mostly visible, never at zero: on a slow phone a stalled first frame must still show
 * the warning, not a blank screen.
 */
@Composable
private fun Modifier.riseIn(entered: Boolean, index: Int): Modifier {
    val progress by animateFloatAsState(
        targetValue = if (entered) 1f else 0f,
        animationSpec = tween(Motion.MEDIUM, delayMillis = index * 55, easing = Motion.EmphasizedDecelerate),
        label = "riseIn$index"
    )
    val risePx = with(LocalDensity.current) { 16.dp.toPx() }
    return graphicsLayer(alpha = 0.75f + 0.25f * progress, translationY = (1f - progress) * risePx)
}

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

    // Entrance: badge springs in, content rises in with a short stagger.
    var entered by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { entered = true }
    val badgeScale by animateFloatAsState(
        targetValue = if (entered) 1f else 0.5f,
        animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessLow),
        label = "badgeScale"
    )

    // Unskippable by back button (back = Hang up and cancel)
    BackHandler {
        onHangUpAndCancel()
    }

    val colors = MaterialTheme.colorScheme
    val formattedAmount = formatAmount(amount)

    Dialog(
        onDismissRequest = { onHangUpAndCancel() },
        properties = DialogProperties(
            dismissOnBackPress = false,
            dismissOnClickOutside = false,
            usePlatformDefaultWidth = false
        )
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Surface(
                modifier = Modifier
                    .fillMaxSize()
                    .systemBarsPadding(),
                color = colors.surface
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                ) {
                    // Header: error-tinted area with badge, headline and the one-line fact
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(
                                colors.errorContainer,
                                MaterialTheme.shapes.extraLarge.copy(
                                    topStart = ZeroCornerSize,
                                    topEnd = ZeroCornerSize
                                )
                            )
                            .padding(horizontal = 24.dp, vertical = 24.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .graphicsLayer {
                                    scaleX = badgeScale
                                    scaleY = badgeScale
                                }
                                .size(72.dp)
                                .background(colors.error, CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = "Security Alert",
                                tint = colors.onError,
                                modifier = Modifier.size(40.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        Column(modifier = Modifier.riseIn(entered, 0)) {
                            BilingualText(
                                en = "Wait. This looks like a scam call.",
                                hi = "रुकिए। यह धोखाधड़ी का फोन कॉल प्रतीत होता है।",
                                style = MaterialTheme.typography.headlineSmall,
                                color = colors.onErrorContainer,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.semantics { heading() }
                            )

                            Spacer(modifier = Modifier.height(12.dp))

                            BilingualText(
                                en = "You are sending ₹$formattedAmount to $payeeVpa.",
                                hi = "आप $payeeVpa को ₹$formattedAmount भेज रहे हैं।",
                                style = MaterialTheme.typography.bodyLarge,
                                color = colors.onErrorContainer
                            )
                        }
                    }

                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 24.dp)
                            .padding(top = 24.dp, bottom = 24.dp)
                    ) {
                        // Reasons from the decision, then the standing advice
                        Column(modifier = Modifier.riseIn(entered, 1)) {
                            val reasonsToShow = decision.reasons.take(3)
                            if (reasonsToShow.isNotEmpty()) {
                                ReasonList(reasons = reasonsToShow, iconTint = colors.error)
                                Spacer(modifier = Modifier.height(20.dp))
                            }

                            Surface(
                                shape = MaterialTheme.shapes.medium,
                                color = colors.surfaceContainerHigh,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.padding(16.dp),
                                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                                    verticalAlignment = Alignment.Top
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Info,
                                        contentDescription = null,
                                        tint = colors.onSurfaceVariant,
                                        modifier = Modifier
                                            .padding(top = 2.dp)
                                            .size(24.dp)
                                    )
                                    BilingualText(
                                        en = "Police and banks never ask you to move money \"for verification\".",
                                        hi = "पुलिस या बैंक कभी \"जाँच\" के लिए पैसे ट्रांसफर करने को नहीं कहते।",
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = colors.onSurface,
                                        fontWeight = FontWeight.Medium,
                                        modifier = Modifier.weight(1f)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(24.dp))

                        // Check question: three large selectable answers
                        Column(modifier = Modifier.riseIn(entered, 2)) {
                            BilingualText(
                                en = "Is someone on the phone telling you what to do?",
                                hi = "क्या फोन पर कोई आपको निर्देश दे रहा है?",
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.onSurface,
                                modifier = Modifier.semantics { heading() }
                            )

                            Spacer(modifier = Modifier.height(12.dp))

                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .selectableGroup(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                listOf(
                                    "Yes" to "हाँ",
                                    "No" to "नहीं",
                                    "Not sure" to "पक्का नहीं"
                                ).forEach { (option, optionHi) ->
                                    val isSelected = selectedQuestionnaireAnswer == option
                                    Surface(
                                        shape = MaterialTheme.shapes.small,
                                        color = if (isSelected) colors.primaryContainer else colors.surface,
                                        contentColor = if (isSelected) colors.onPrimaryContainer else colors.onSurface,
                                        border = BorderStroke(
                                            width = if (isSelected) 2.dp else 1.dp,
                                            color = if (isSelected) colors.primary else colors.outline
                                        ),
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .heightIn(min = 56.dp)
                                                .selectable(
                                                    selected = isSelected,
                                                    role = Role.RadioButton,
                                                    onClick = {
                                                        selectedQuestionnaireAnswer = option
                                                        if (!questionnaireSubmitted) {
                                                            questionnaireSubmitted = true
                                                            coroutineScope.launch {
                                                                val isGuiding = (option == "Yes")
                                                                RiskGate.sendQuestionnaireAnswer(decision.caseId, isGuiding)
                                                            }
                                                        }
                                                    }
                                                )
                                                .padding(horizontal = 4.dp, vertical = 8.dp),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            BilingualText(
                                                en = option,
                                                hi = optionHi,
                                                style = MaterialTheme.typography.titleMedium,
                                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                                textAlign = TextAlign.Center
                                            )
                                        }
                                    }
                                }
                            }

                            AnimatedVisibility(
                                visible = selectedQuestionnaireAnswer == "Yes",
                                enter = fadeIn(tween(Motion.MEDIUM)),
                                exit = fadeOut(tween(Motion.SHORT))
                            ) {
                                BilingualText(
                                    en = "Hang up now. A real bank or police officer will never tell you to pay.",
                                    hi = "अभी फोन काट दें। असली बैंक या पुलिस अधिकारी कभी पैसे भेजने को नहीं कहते।",
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = colors.onSurface,
                                    fontWeight = FontWeight.Medium,
                                    modifier = Modifier
                                        .padding(top = 12.dp)
                                        .semantics { liveRegion = LiveRegionMode.Polite }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(24.dp))

                        // Actions
                        Column(modifier = Modifier.riseIn(entered, 3)) {
                            // 1. Hang up and cancel (primary, safe)
                            Button(
                                onClick = onHangUpAndCancel,
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = colors.error,
                                    contentColor = colors.onError
                                ),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 56.dp)
                                    .semantics { contentDescription = "Hang up call and cancel payment" }
                            ) {
                                Icon(Icons.Default.CallEnd, contentDescription = null, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.width(12.dp))
                                BilingualLabel(
                                    en = "Hang Up & Cancel Payment",
                                    hi = "फोन काटें और भुगतान रद्द करें"
                                )
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            // 2. Ask my trusted contact
                            OutlinedButton(
                                onClick = { showTrustedContactSheet = true },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 56.dp)
                                    .semantics { contentDescription = "Ask trusted contact for advice" }
                            ) {
                                Icon(Icons.Default.People, contentDescription = null, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.width(12.dp))
                                BilingualLabel(
                                    en = "Ask My Trusted Contact",
                                    hi = "अपने विश्वसनीय संपर्क से पूछें"
                                )
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            // 3. Continue after hold: disabled with a calm live countdown
                            OutlinedButton(
                                onClick = {
                                    if (isHoldComplete) {
                                        showFinalReleaseWarning = true
                                    }
                                },
                                enabled = isHoldComplete,
                                colors = ButtonDefaults.outlinedButtonColors(
                                    disabledContentColor = colors.onSurfaceVariant
                                ),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 56.dp)
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
                                    modifier = Modifier.size(24.dp)
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                if (isHoldComplete) {
                                    Text(
                                        text = "Continue to PIN (Hold Ended)",
                                        style = MaterialTheme.typography.titleMedium
                                    )
                                } else {
                                    Text(
                                        text = "Continue after ",
                                        style = MaterialTheme.typography.titleMedium
                                    )
                                    AnimatedContent(
                                        targetState = timeFormatted,
                                        transitionSpec = {
                                            (slideInVertically(tween(Motion.SHORT)) { it / 4 } + fadeIn(tween(Motion.SHORT))) togetherWith
                                                (slideOutVertically(tween(Motion.SHORT)) { -it / 4 } + fadeOut(tween(Motion.SHORT)))
                                        },
                                        label = "holdCountdown"
                                    ) { time ->
                                        Text(
                                            text = time,
                                            style = MaterialTheme.typography.titleMedium.copy(
                                                fontFeatureSettings = "tnum"
                                            )
                                        )
                                    }
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // 4. Report a scam: opens the 1930 flow
                        TextButton(
                            onClick = { showReportSheet = true },
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 48.dp)
                                .riseIn(entered, 4)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Security,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Report a scam (Call 1930 / cybercrime.gov.in)",
                                style = MaterialTheme.typography.titleSmall,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
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

            // Release-after-hold: final warning before the PIN screen. "Back to safety" is the filled choice.
            if (showFinalReleaseWarning) {
                AlertDialog(
                    onDismissRequest = { showFinalReleaseWarning = false },
                    title = {
                        BilingualText(
                            en = "Final Caution Notice",
                            hi = "अंतिम चेतावनी",
                            style = MaterialTheme.typography.headlineSmall,
                            color = colors.error
                        )
                    },
                    text = {
                        BilingualText(
                            en = "The 30-minute safety pause has elapsed. If anyone is coaching you on the phone, hang up now. Once the PIN is entered, funds cannot be reversed.",
                            hi = "30 मिनट का सुरक्षा विराम पूरा हो गया। अगर फोन पर कोई आपको निर्देश दे रहा है, तो अभी फोन काट दें। PIN डालने के बाद पैसे वापस नहीं आ सकते।",
                            style = MaterialTheme.typography.bodyLarge,
                            modifier = Modifier.verticalScroll(rememberScrollState())
                        )
                    },
                    confirmButton = {
                        Button(
                            onClick = { showFinalReleaseWarning = false },
                            modifier = Modifier.heightIn(min = 56.dp)
                        ) {
                            Text("Back to safety", style = MaterialTheme.typography.titleMedium)
                        }
                    },
                    dismissButton = {
                        TextButton(
                            onClick = {
                                showFinalReleaseWarning = false
                                onProceedAfterHold()
                            },
                            modifier = Modifier.heightIn(min = 48.dp)
                        ) {
                            Text("I understand, enter PIN", style = MaterialTheme.typography.titleSmall)
                        }
                    }
                )
            }
        }
    }
}
