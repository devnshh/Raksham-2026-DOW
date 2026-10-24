package com.raksham.upi.ui.components

import com.raksham.upi.ui.formatAmount
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import com.raksham.risk.model.PlainReason
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportScamSheet(
    payeeVpa: String,
    amount: Double,
    reasons: List<PlainReason>,
    caseId: String,
    onDismiss: () -> Unit,
    /** Cancels the payment, files the report, then opens [intent] (the dialer or the portal). */
    onReportAndLeave: (intent: Intent) -> Unit
) {
    val clipboardManager = LocalClipboardManager.current
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val colors = MaterialTheme.colorScheme
    val formattedTime = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())

    val incidentSummary = buildString {
        appendLine("--- SUSPECTED FRAUD INCIDENT REPORT ---")
        appendLine("Date/Time: $formattedTime")
        appendLine("Recipient UPI ID: $payeeVpa")
        appendLine("Attempted Amount: ₹${formatAmount(amount)}")
        if (caseId.isNotBlank()) {
            appendLine("Incident Ref ID: $caseId")
        }
        appendLine("Detected Risk Signals:")
        reasons.forEach {
            appendLine("- ${it.en}")
        }
        appendLine("---------------------------------------")
    }

    InlineSheet(onDismiss = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
                .padding(top = 8.dp, bottom = 24.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .background(colors.errorContainer, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Security,
                    contentDescription = "Report Scam",
                    tint = colors.onErrorContainer,
                    modifier = Modifier.size(32.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            BilingualText(
                en = "Report Fraudulent Transaction",
                hi = "साइबर वित्तीय धोखाधड़ी की शिकायत दर्ज करें",
                style = MaterialTheme.typography.headlineSmall,
                color = colors.onSurface,
                modifier = Modifier.semantics { heading() }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Primary: call 1930 (ACTION_DIAL intent)
            Button(
                onClick = { onReportAndLeave(Intent(Intent.ACTION_DIAL, Uri.parse("tel:1930"))) },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp)
                    .semantics { contentDescription = "Call National Cybercrime Helpline 1930" }
            ) {
                Icon(Icons.Default.Call, contentDescription = null, modifier = Modifier.size(24.dp))
                Spacer(modifier = Modifier.width(12.dp))
                BilingualLabel(en = "Call National Helpline 1930", hi = "राष्ट्रीय हेल्पलाइन 1930 पर कॉल करें")
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Open cybercrime.gov.in (ACTION_VIEW intent)
            FilledTonalButton(
                onClick = { onReportAndLeave(Intent(Intent.ACTION_VIEW, Uri.parse("https://cybercrime.gov.in"))) },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp)
                    .semantics { contentDescription = "Open cybercrime.gov.in portal" }
            ) {
                Icon(Icons.Default.Language, contentDescription = null, modifier = Modifier.size(24.dp))
                Spacer(modifier = Modifier.width(12.dp))
                BilingualLabel(en = "Open cybercrime.gov.in", hi = "cybercrime.gov.in खोलें")
            }

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedButton(
                onClick = {
                    clipboardManager.setText(AnnotatedString(incidentSummary))
                    scope.launch { snackbarHostState.showSnackbar("Incident summary copied to clipboard") }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp)
                    .semantics { contentDescription = "Copy incident summary to clipboard" }
            ) {
                Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(24.dp))
                Spacer(modifier = Modifier.width(12.dp))
                BilingualLabel(en = "Copy Incident Summary", hi = "घटना का सारांश कॉपी करें")
            }

            SnackbarHost(
                hostState = snackbarHostState,
                modifier = Modifier.padding(top = 12.dp)
            )
        }
    }
}
