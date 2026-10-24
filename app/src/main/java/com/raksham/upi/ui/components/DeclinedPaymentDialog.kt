package com.raksham.upi.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Block
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.SecureFlagPolicy
import com.raksham.risk.RiskGate
import com.raksham.risk.model.RiskDecision
import kotlinx.coroutines.launch

/**
 * Shown only when an analyst has confirmed the payee as a scam account (tier DECLINE).
 * There is deliberately no "continue" button: the payment cannot reach the PIN screen.
 */
@Composable
fun DeclinedPaymentDialog(
    decision: RiskDecision,
    payeeName: String,
    onClose: () -> Unit
) {
    val context = LocalContext.current
    val colors = MaterialTheme.colorScheme

    AlertDialog(
        onDismissRequest = onClose,
        // Secure window (FLAG_SECURE): screen sharing, casting, recording and screenshots show it blank, so a
        // scammer watching the screen cannot read the warning or see which button is tapped. The user sees it normally.
        properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn),
        icon = {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .background(colors.errorContainer, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Block,
                    contentDescription = "Payment blocked",
                    tint = colors.onErrorContainer,
                    modifier = Modifier.size(32.dp)
                )
            }
        },
        title = {
            BilingualText(
                en = "Payment blocked",
                hi = "भुगतान रोक दिया गया",
                style = MaterialTheme.typography.headlineSmall,
                color = colors.onSurface,
                modifier = Modifier.semantics { heading() }
            )
        },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                BilingualText(
                    en = "We stopped this payment to $payeeName. The bank has confirmed this account as fraud.",
                    hi = "$payeeName को यह भुगतान रोक दिया गया है। बैंक ने इस खाते को धोखाधड़ी वाला माना है।",
                    style = MaterialTheme.typography.bodyLarge,
                    color = colors.onSurface,
                    fontWeight = FontWeight.Medium
                )
                if (decision.reasons.isNotEmpty()) {
                    ReasonList(reasons = decision.reasons, iconTint = colors.error)
                }
                BilingualText(
                    en = "If you were asked to pay this account, it is a scam. If you think this is a mistake, report a false alarm: a person at the bank reviews case ${decision.caseId}.",
                    hi = "अगर किसी ने आपसे इस खाते में पैसे भेजने को कहा है, तो यह धोखाधड़ी है। गलती लगे तो गलत चेतावनी की शिकायत करें: बैंक का कर्मचारी केस ${decision.caseId} की समीक्षा करेगा।",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.onSurfaceVariant
                )
                ReportFalseAlarmButton(caseId = decision.caseId)
            }
        },
        confirmButton = {
            Button(
                onClick = onClose,
                modifier = Modifier.heightIn(min = 56.dp)
            ) {
                Text("OK", style = MaterialTheme.typography.titleMedium)
            }
        },
        dismissButton = {
            TextButton(
                onClick = {
                    context.startActivity(
                        Intent(Intent.ACTION_DIAL).apply { data = Uri.parse("tel:1930") }
                    )
                },
                modifier = Modifier.heightIn(min = 48.dp)
            ) {
                Text("Report scam: call 1930", style = MaterialTheme.typography.titleSmall)
            }
        }
    )
}

/**
 * Red pause and decline: the only appeal is a report an analyst reviews. It changes nothing on the
 * spot, so a scammer coaching the user gains nothing by asking them to tap it.
 */
@Composable
internal fun ReportFalseAlarmButton(caseId: String, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var sent by remember(caseId) { mutableStateOf<Boolean?>(null) }
    if (sent == true) {
        BilingualText(
            en = "Sent to the bank for review. Nothing changes until an analyst checks it.",
            hi = "बैंक को समीक्षा के लिए भेजा गया। विश्लेषक की जांच तक कुछ नहीं बदलेगा।",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = modifier.semantics { liveRegion = LiveRegionMode.Polite }
        )
        return
    }
    Column(modifier = modifier) {
        TextButton(
            onClick = { scope.launch { sent = RiskGate.reportFalseAlarm(caseId) } },
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
        ) {
            BilingualLabel(en = "Report a false alarm", hi = "गलत चेतावनी की शिकायत करें")
        }
        if (sent == false) {
            BilingualText(
                en = "Could not send. Check the connection and try again.",
                hi = "भेजा नहीं जा सका। कनेक्शन जांचकर फिर से कोशिश करें।",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
            )
        }
    }
}
