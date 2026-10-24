package com.raksham.upi.ui.screens

import android.widget.Toast
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.risk.RiskGate
import com.raksham.risk.model.PaymentRequest
import com.raksham.risk.model.RiskDecision
import com.raksham.risk.model.RiskTier
import com.raksham.risk.session.SessionTracker
import com.raksham.upi.data.BankAccount
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.components.AmberWarningDialog
import com.raksham.upi.ui.components.DeclinedPaymentDialog
import com.raksham.upi.ui.components.NpciPinBottomSheet
import com.raksham.upi.ui.components.RedSmartPauseDialog
import com.raksham.upi.ui.theme.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Test & Scenario Controller hooks allowing the Scenario Player
 * to programmatically drive the UI with visible typing and taps.
 */
object PaymentScreenController {
    var programmaticAmount: String? = null
    var programmaticNote: String? = null
    var onRequestPayAction: (() -> Unit)? = null
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PaymentAmountScreen(
    contact: Contact,
    initialAmount: Double?,
    entryChannel: String,
    onBackClick: () -> Unit,
    onPaymentSuccess: (amount: Double, contact: Contact, upiRefId: String) -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val focusManager = LocalFocusManager.current

    var amountText by remember { mutableStateOf(initialAmount?.let { String.format("%.0f", it) } ?: "") }
    var noteText by remember { mutableStateOf("") }
    var selectedBank by remember { mutableStateOf(MockData.linkedBankAccounts.first()) }

    // Interception State
    var currentDecision by remember { mutableStateOf<RiskDecision?>(null) }
    var showRedSmartPause by remember { mutableStateOf(false) }
    var showAmberWarning by remember { mutableStateOf(false) }
    var showDeclined by remember { mutableStateOf(false) }
    var showPinSheet by remember { mutableStateOf(false) }
    var checkedPayment by remember { mutableStateOf<PaymentRequest?>(null) }
    var pinShownAtMs by remember { mutableStateOf(0L) }

    // New payment session: typing rhythm and app switches are measured from here.
    LaunchedEffect(Unit) { SessionTracker.startPaymentSession() }
    LaunchedEffect(showPinSheet) { if (showPinSheet) pinShownAtMs = System.currentTimeMillis() }

    // Progress State: Show subtle progress indicator ONLY after 300ms
    var isAssessingRisk by remember { mutableStateOf(false) }
    var showSubtleProgress by remember { mutableStateOf(false) }

    val parsedAmount = amountText.toDoubleOrNull() ?: 0.0
    val isButtonEnabled = parsedAmount > 0.0 && !isAssessingRisk

    // Listen for scenario automation inputs
    LaunchedEffect(PaymentScreenController.programmaticAmount) {
        PaymentScreenController.programmaticAmount?.let {
            amountText = it
        }
    }
    LaunchedEffect(PaymentScreenController.programmaticNote) {
        PaymentScreenController.programmaticNote?.let {
            noteText = it
        }
    }

    fun initiateRiskCheck() {
        if (parsedAmount <= 0.0 || isAssessingRisk) return

        focusManager.clearFocus()
        isAssessingRisk = true
        showSubtleProgress = false

        coroutineScope.launch {
            // Subtle progress appears only after 300 ms
            val timerJob = launch {
                delay(300L)
                if (isAssessingRisk) {
                    showSubtleProgress = true
                }
            }

            val paymentRequest = PaymentRequest(
                payeeVpa = contact.upiId,
                amount = parsedAmount,
                payeeDisplayName = contact.name,
                noteText = noteText,
                entryChannel = entryChannel,
                userRef = "raksham@oksbi"
            )

            val decision = RiskGate.check(paymentRequest)
            checkedPayment = paymentRequest

            timerJob.cancel()
            isAssessingRisk = false
            showSubtleProgress = false
            currentDecision = decision

            when (decision.tier) {
                RiskTier.GREEN -> {
                    // GREEN: nothing is shown, straight to PIN
                    showPinSheet = true
                }
                RiskTier.AMBER -> {
                    showAmberWarning = true
                }
                RiskTier.RED -> {
                    showRedSmartPause = true
                }
                RiskTier.DECLINE -> {
                    // Analyst-confirmed scam payee: no PIN, no "continue" path.
                    showDeclined = true
                }
            }
        }
    }

    LaunchedEffect(Unit) {
        PaymentScreenController.onRequestPayAction = {
            initiateRiskCheck()
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            PaymentScreenController.onRequestPayAction = null
            PaymentScreenController.programmaticAmount = null
            PaymentScreenController.programmaticNote = null
        }
    }

    val amountFocus = remember { FocusRequester() }
    LaunchedEffect(Unit) { amountFocus.requestFocus() }

    // The amount grows from the centre as digits are typed, then steps down so long values still fit.
    val amountSize by animateFloatAsState(
        targetValue = when (amountText.length) {
            in 0..3 -> 56f
            4 -> 52f
            5 -> 46f
            6 -> 40f
            else -> 36f
        },
        animationSpec = tween(Motion.MEDIUM, easing = Motion.Emphasized),
        label = "amount size"
    )
    val amountStyle = MaterialTheme.typography.displayLarge.copy(
        fontSize = amountSize.sp,
        lineHeight = (amountSize * 1.15f).sp,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = TextAlign.Center
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {},
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .consumeWindowInsets(padding)
                    .imePadding()
            ) {
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp)
                        .verticalScroll(rememberScrollState()),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Spacer(modifier = Modifier.height(8.dp))

                    Surface(
                        modifier = Modifier.size(64.dp),
                        shape = CircleShape,
                        color = Color(contact.colorHex)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = contact.avatarInitials,
                                style = MaterialTheme.typography.titleLarge,
                                color = Color.White
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = contact.name,
                            style = MaterialTheme.typography.titleLarge,
                            color = MaterialTheme.colorScheme.onSurface,
                            textAlign = TextAlign.Center
                        )
                        if (contact.isVerified) {
                            Spacer(modifier = Modifier.width(6.dp))
                            Icon(
                                imageVector = Icons.Filled.Verified,
                                contentDescription = "Verified Payee",
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }
                    Text(
                        text = contact.upiId,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Spacer(modifier = Modifier.height(32.dp))

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.Center
                    ) {
                        Text(text = "₹", style = amountStyle)
                        Spacer(modifier = Modifier.width(4.dp))
                        BasicTextField(
                            value = amountText,
                            onValueChange = {
                                if (it.length <= 7 && it.all { c -> c.isDigit() }) {
                                    amountText = it
                                    SessionTracker.onKeystroke()
                                }
                            },
                            textStyle = amountStyle,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            singleLine = true,
                            cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                            modifier = Modifier
                                .width(IntrinsicSize.Min)
                                .focusRequester(amountFocus),
                            decorationBox = { inner ->
                                Box(contentAlignment = Alignment.Center) {
                                    if (amountText.isEmpty()) {
                                        Text(
                                            text = "0",
                                            style = amountStyle,
                                            color = MaterialTheme.colorScheme.outlineVariant
                                        )
                                    }
                                    inner()
                                }
                            }
                        )
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    TextField(
                        value = noteText,
                        onValueChange = {
                            noteText = it
                            SessionTracker.onKeystroke()
                        },
                        placeholder = {
                            Text(
                                text = "Add a note",
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center
                            )
                        },
                        textStyle = MaterialTheme.typography.bodyLarge.copy(textAlign = TextAlign.Center),
                        singleLine = true,
                        shape = CircleShape,
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                            unfocusedContainerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent,
                            disabledIndicatorColor = Color.Transparent
                        ),
                        modifier = Modifier
                            .fillMaxWidth(0.7f)
                            .widthIn(min = 200.dp, max = 320.dp)
                    )

                    Spacer(modifier = Modifier.height(16.dp))
                }

                Column(modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 16.dp)) {
                    Surface(
                        shape = MaterialTheme.shapes.medium,
                        color = MaterialTheme.colorScheme.surfaceContainerLow,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 64.dp)
                                .padding(horizontal = 16.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Surface(
                                modifier = Modifier.size(40.dp),
                                shape = CircleShape,
                                color = MaterialTheme.colorScheme.primaryContainer
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Icon(
                                        imageVector = Icons.Filled.AccountBalance,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.onPrimaryContainer,
                                        modifier = Modifier.size(20.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.width(16.dp))

                            Column {
                                Text(
                                    text = selectedBank.bankName,
                                    style = MaterialTheme.typography.titleMedium,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = "${selectedBank.accountType} (${selectedBank.accountNumberMasked})",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Stays enabled while checking (initiateRiskCheck ignores re-entry) so the button keeps
                    // its colour and shows progress inline instead of greying out.
                    Button(
                        onClick = { initiateRiskCheck() },
                        enabled = parsedAmount > 0.0,
                        shape = CircleShape,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp)
                            .semantics { contentDescription = "Pay button" }
                    ) {
                        AnimatedContent(
                            targetState = showSubtleProgress,
                            transitionSpec = {
                                fadeIn(tween(Motion.SHORT, delayMillis = 60, easing = Motion.EmphasizedDecelerate))
                                    .togetherWith(fadeOut(tween(90)))
                            },
                            label = "pay button state"
                        ) { checking ->
                            if (checking) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    CircularProgressIndicator(
                                        strokeWidth = 2.dp,
                                        color = LocalContentColor.current,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Text("Checking...", style = MaterialTheme.typography.titleMedium)
                                }
                            } else {
                                Text(
                                    text = if (parsedAmount > 0) "Pay ₹${String.format("%,.0f", parsedAmount)}" else "Enter Amount",
                                    style = MaterialTheme.typography.titleMedium
                                )
                            }
                        }
                    }
                }
            }

            // RED Tier Pause Screen
            if (showRedSmartPause && currentDecision != null) {
                RedSmartPauseDialog(
                    decision = currentDecision!!,
                    payeeVpa = contact.upiId,
                    amount = parsedAmount,
                    onHangUpAndCancel = {
                        showRedSmartPause = false
                        Toast.makeText(context, "Payment cancelled safely.", Toast.LENGTH_LONG).show()
                        onBackClick()
                    },
                    onAskTrustedContact = {
                        // Handled inside RedSmartPauseDialog
                    },
                    onProceedAfterHold = {
                        showRedSmartPause = false
                        showPinSheet = true
                    }
                )
            }

            // DECLINE: blocked payment, reasons and how to appeal (never a path to the PIN screen)
            if (showDeclined && currentDecision != null) {
                DeclinedPaymentDialog(
                    decision = currentDecision!!,
                    payeeName = contact.name,
                    onClose = {
                        showDeclined = false
                        onBackClick()
                    }
                )
            }

            // AMBER Tier Caution Dialog
            if (showAmberWarning && currentDecision != null) {
                AmberWarningDialog(
                    decision = currentDecision!!,
                    payeeName = contact.name,
                    amount = parsedAmount,
                    onContinue = {
                        showAmberWarning = false
                        showPinSheet = true
                    },
                    onCancel = {
                        showAmberWarning = false
                    }
                )
            }

            // NPCI UPI PIN Keypad Bottom Sheet
            if (showPinSheet) {
                NpciPinBottomSheet(
                    payeeName = contact.name,
                    amount = parsedAmount,
                    bankAccount = selectedBank,
                    onPinSuccess = {
                        showPinSheet = false
                        // Only now is it a payment: tell the server so baselines and fan-in update.
                        val decisionNow = currentDecision
                        val paymentNow = checkedPayment
                        val pinSecs = if (pinShownAtMs > 0L) (System.currentTimeMillis() - pinShownAtMs) / 1000.0 else null
                        if (decisionNow != null && paymentNow != null) {
                            // Background scope: this screen is about to be left for the receipt.
                            RiskGate.reportPaymentCompletedInBackground(decisionNow.caseId, paymentNow, pinSecs)
                        }
                        val refId = "4291" + (10000000..99999999).random().toString()
                        onPaymentSuccess(parsedAmount, contact, refId)
                    },
                    onDismiss = {
                        showPinSheet = false
                    }
                )
            }
        }
    }
}
