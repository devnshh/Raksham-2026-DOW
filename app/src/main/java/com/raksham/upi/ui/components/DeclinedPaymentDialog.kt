package com.raksham.upi.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.risk.model.RiskDecision
import com.raksham.upi.ui.theme.*

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
    AlertDialog(
        onDismissRequest = onClose,
        title = {
            Text(
                text = "Payment blocked",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = GPayRed
            )
        },
        text = {
            Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                Text(
                    text = "We stopped this payment to $payeeName. भुगतान रोक दिया गया है।",
                    fontSize = 15.sp,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(10.dp))
                decision.reasons.forEach { reason ->
                    Text(text = "• ${reason.en}", fontSize = 13.sp, color = TextPrimary)
                    Text(text = "  ${reason.hi}", fontSize = 12.sp, color = TextMuted)
                    Spacer(modifier = Modifier.height(4.dp))
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "If you were asked to pay this account, it is a scam: call 1930 or report at " +
                        "cybercrime.gov.in. If you think this is a mistake, contact support with case ${decision.caseId} " +
                        "to appeal. A human reviews every appeal.",
                    fontSize = 12.sp,
                    color = TextSecondary
                )
            }
        },
        confirmButton = {
            Button(onClick = onClose) { Text("Close") }
        }
    )
}
