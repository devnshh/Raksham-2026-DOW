package com.raksham.upi.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
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

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Paying ${contact.name}", fontSize = 17.sp, fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        containerColor = SurfaceBackground
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp)
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Spacer(modifier = Modifier.height(12.dp))

                // Recipient Profile Card
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = Color.White,
                    tonalElevation = 1.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Surface(
                            modifier = Modifier.size(48.dp),
                            shape = CircleShape,
                            color = Color(contact.colorHex)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text(
                                    text = contact.avatarInitials,
                                    fontSize = 17.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                            }
                        }

                        Spacer(modifier = Modifier.width(14.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = contact.name,
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary
                                )
                                if (contact.isVerified) {
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Icon(
                                        imageVector = Icons.Default.CheckCircle,
                                        contentDescription = "Verified Payee",
                                        tint = GPayBlue,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                            Text(
                                text = contact.upiId,
                                fontSize = 13.sp,
                                color = TextSecondary,
                                modifier = Modifier.padding(top = 2.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Amount Entry Card
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = Color.White,
                    tonalElevation = 1.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "Enter Amount",
                            fontSize = 13.sp,
                            color = TextSecondary,
                            fontWeight = FontWeight.Medium
                        )

                        Spacer(modifier = Modifier.height(10.dp))

                        // Large Rupee Input
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Text(
                                text = "₹",
                                fontSize = 38.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            OutlinedTextField(
                                value = amountText,
                                onValueChange = {
                                    if (it.length <= 7 && it.all { c -> c.isDigit() }) {
                                        amountText = it
                                        SessionTracker.onKeystroke()
                                    }
                                },
                                placeholder = { Text("0", fontSize = 36.sp, color = TextMuted) },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                singleLine = true,
                                textStyle = LocalTextStyle.current.copy(
                                    fontSize = 38.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary,
                                    textAlign = TextAlign.Start
                                ),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = Color.Transparent,
                                    unfocusedBorderColor = Color.Transparent
                                ),
                                modifier = Modifier.width(IntrinsicSize.Min)
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Quick preset chips (+₹100, +₹500, +₹2,000, +₹10,000)
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            listOf(100, 500, 2000, 10000).forEach { chipAmount ->
                                Surface(
                                    shape = RoundedCornerShape(16.dp),
                                    color = SurfaceBackground,
                                    modifier = Modifier
                                        .weight(1f)
                                        .clip(RoundedCornerShape(16.dp))
                                        .clickable {
                                            val current = amountText.toDoubleOrNull() ?: 0.0
                                            amountText = String.format("%.0f", current + chipAmount)
                                        }
                                ) {
                                    Text(
                                        text = "+₹$chipAmount",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TextSecondary,
                                        textAlign = TextAlign.Center,
                                        modifier = Modifier.padding(vertical = 8.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        // Payment Note Field
                        OutlinedTextField(
                            value = noteText,
                            onValueChange = {
                                noteText = it
                                SessionTracker.onKeystroke()
                            },
                            placeholder = { Text("Add a note (e.g. dinner, rent)", color = TextMuted, fontSize = 13.sp) },
                            leadingIcon = {
                                Icon(Icons.Default.EditNote, contentDescription = null, tint = GPayBlue)
                            },
                            singleLine = true,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Bank Account Selector Card
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = Color.White,
                    tonalElevation = 1.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Surface(
                            modifier = Modifier.size(36.dp),
                            shape = RoundedCornerShape(8.dp),
                            color = GPayBlueLight
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.AccountBalance,
                                    contentDescription = null,
                                    tint = GPayBlue,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = selectedBank.bankName,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Text(
                                text = "${selectedBank.accountType} (${selectedBank.accountNumberMasked})",
                                fontSize = 12.sp,
                                color = TextMuted
                            )
                        }

                        Text(
                            text = "PRIMARY",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = GPayBlue
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Subtle Progress Indicator (visible only after 300 ms)
                if (showSubtleProgress) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            strokeWidth = 2.dp,
                            modifier = Modifier.size(16.dp),
                            color = GPayBlue
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Verifying payment details...",
                            fontSize = 13.sp,
                            color = TextSecondary
                        )
                    }
                }

                Button(
                    onClick = { initiateRiskCheck() },
                    enabled = isButtonEnabled,
                    colors = ButtonDefaults.buttonColors(containerColor = GPayBlue),
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                        .semantics { contentDescription = "Pay button" }
                ) {
                    Text(
                        text = if (parsedAmount > 0) "Pay ₹${String.format("%,.0f", parsedAmount)}" else "Enter Amount",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))
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
