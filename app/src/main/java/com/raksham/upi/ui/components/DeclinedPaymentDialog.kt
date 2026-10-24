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
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.raksham.risk.model.RiskDecision

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
                    en = "If you were asked to pay this account, it is a scam. If you think this is a mistake, contact support with case ${decision.caseId} to appeal. A human reviews every appeal.",
                    hi = "अगर किसी ने आपसे इस खाते में पैसे भेजने को कहा है, तो यह धोखाधड़ी है। गलती लगे तो केस ${decision.caseId} के साथ सहायता से संपर्क करें। हर अपील की समीक्षा इंसान करता है।",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.onSurfaceVariant
                )
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
