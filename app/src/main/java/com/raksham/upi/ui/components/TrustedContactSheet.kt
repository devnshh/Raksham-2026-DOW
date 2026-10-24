package com.raksham.upi.ui.components

import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

enum class TrustedContactStatus {
    IDLE,
    WAITING,
    APPROVED,
    DECLINED
}

object SimulatedTrustedContactController {
    var scriptedOutcome: TrustedContactStatus = TrustedContactStatus.IDLE
    var autoRespondDelayMs: Long = 3000L
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrustedContactSheet(
    contactFirstName: String = "Aarav",
    payeeName: String,
    amount: Double,
    onDismiss: () -> Unit,
    onDeclined: () -> Unit,
    onApproved: () -> Unit
) {
    var status by remember { mutableStateOf(TrustedContactStatus.IDLE) }
    val formattedAmount = String.format("%,.0f", amount)
    val colors = MaterialTheme.colorScheme

    val messageEn = "$contactFirstName, I am about to send ₹$formattedAmount to $payeeName (new account). Is this safe?"
    val messageHi = "$contactFirstName, मैं $payeeName को ₹$formattedAmount भेज रहा हूँ। क्या यह सुरक्षित है?"

    LaunchedEffect(status) {
        if (status == TrustedContactStatus.WAITING) {
            delay(SimulatedTrustedContactController.autoRespondDelayMs)
            val outcome = if (SimulatedTrustedContactController.scriptedOutcome != TrustedContactStatus.IDLE) {
                SimulatedTrustedContactController.scriptedOutcome
            } else {
                TrustedContactStatus.APPROVED
            }
            status = outcome
            if (outcome == TrustedContactStatus.DECLINED) {
                delay(1200L)
                onDeclined()
            } else if (outcome == TrustedContactStatus.APPROVED) {
                delay(1200L)
                onApproved()
            }
        }
    }

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = colors.surface) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
                .padding(top = 8.dp, bottom = 24.dp)
        ) {
            BilingualText(
                en = "Ask $contactFirstName (Trusted Contact)",
                hi = "विश्वसनीय संपर्क से पुष्टि करें",
                style = MaterialTheme.typography.headlineSmall,
                color = colors.onSurface,
                modifier = Modifier.semantics { heading() }
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Contact row: avatar initial, name, role
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 72.dp)
                    .semantics(mergeDescendants = true) { contentDescription = "Trusted Contact $contactFirstName" },
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .background(colors.primaryContainer, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = contactFirstName.take(1).uppercase(),
                        style = MaterialTheme.typography.titleLarge,
                        color = colors.onPrimaryContainer
                    )
                }
                Column {
                    Text(
                        text = contactFirstName,
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.onSurface
                    )
                    Text(
                        text = "Trusted contact",
                        style = MaterialTheme.typography.bodyMedium,
                        color = colors.onSurfaceVariant
                    )
                    Text(
                        text = "विश्वसनीय संपर्क",
                        style = MaterialTheme.typography.bodyMedium,
                        color = colors.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Crossfade(
                targetState = status,
                label = "trustedContactStatus",
                modifier = Modifier
                    .fillMaxWidth()
                    .animateContentSize()
            ) { current ->
                when (current) {
                    TrustedContactStatus.IDLE -> {
                        Column(modifier = Modifier.fillMaxWidth()) {
                            Surface(
                                shape = MaterialTheme.shapes.medium,
                                color = colors.surfaceContainerHigh,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Text(
                                        text = "Message Preview:",
                                        style = MaterialTheme.typography.labelLarge,
                                        color = colors.onSurfaceVariant
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    BilingualText(
                                        en = "\"$messageEn\"",
                                        hi = "\"$messageHi\"",
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = colors.onSurface
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(24.dp))

                            Button(
                                onClick = { status = TrustedContactStatus.WAITING },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 56.dp)
                                    .semantics { contentDescription = "Send verification request to $contactFirstName" }
                            ) {
                                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = null, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.width(12.dp))
                                BilingualLabel(en = "Send Verification Request", hi = "पुष्टि का अनुरोध भेजें")
                            }
                        }
                    }

                    TrustedContactStatus.WAITING -> {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .semantics { liveRegion = LiveRegionMode.Polite },
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            CircularProgressIndicator(modifier = Modifier.size(40.dp))
                            BilingualText(
                                en = "Waiting for $contactFirstName's response...",
                                hi = "$contactFirstName के उत्तर की प्रतीक्षा की जा रही है...",
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.onSurface,
                                textAlign = TextAlign.Center
                            )
                        }
                    }

                    TrustedContactStatus.APPROVED -> {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .semantics { liveRegion = LiveRegionMode.Polite },
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.CheckCircle,
                                contentDescription = "Approved",
                                tint = colors.tertiary,
                                modifier = Modifier.size(48.dp)
                            )
                            BilingualText(
                                en = "$contactFirstName responded: Payment looks okay.",
                                hi = "$contactFirstName ने जवाब दिया: भुगतान ठीक लगता है।",
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.onSurface,
                                textAlign = TextAlign.Center
                            )
                            BilingualText(
                                en = "Note: Safety hold countdown is still running.",
                                hi = "ध्यान दें: सुरक्षा विराम की गिनती अभी चल रही है।",
                                style = MaterialTheme.typography.bodyMedium,
                                color = colors.onSurfaceVariant,
                                textAlign = TextAlign.Center
                            )
                        }
                    }

                    TrustedContactStatus.DECLINED -> {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .semantics { liveRegion = LiveRegionMode.Polite },
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Declined",
                                tint = colors.error,
                                modifier = Modifier.size(48.dp)
                            )
                            BilingualText(
                                en = "$contactFirstName warned: Do not proceed! Suspected scam.",
                                hi = "$contactFirstName ने सलाह दी है कि यह धोखाधड़ी हो सकती है। भुगतान रद्द किया गया।",
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.error,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
            }
        }
    }
}
