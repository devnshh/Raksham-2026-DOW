package com.raksham.upi.ui.components

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import com.raksham.upi.ui.formatAmount
import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Sms
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/** Hands the question to the phone's own SMS or WhatsApp app. The reply comes back there, from a real
 *  person; nothing here pretends to answer for them, and the safety hold keeps running meanwhile. */
private fun smsIntent(text: String) =
    Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:")).putExtra("sms_body", text)

private fun whatsAppIntent(text: String) =
    Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/?text=" + Uri.encode(text)))

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrustedContactSheet(
    contactFirstName: String = "Aarav",
    payeeName: String,
    amount: Double,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var sentVia by remember { mutableStateOf<String?>(null) }
    var noApp by remember { mutableStateOf(false) }
    val formattedAmount = formatAmount(amount)
    val colors = MaterialTheme.colorScheme

    val messageEn = "$contactFirstName, I am about to send ₹$formattedAmount to $payeeName (new account). Is this safe?"
    val messageHi = "$contactFirstName, मैं $payeeName को ₹$formattedAmount भेज रहा हूँ। क्या यह सुरक्षित है?"

    fun send(intent: Intent, via: String) {
        try {
            context.startActivity(intent)
            sentVia = via
            noApp = false
        } catch (e: ActivityNotFoundException) {
            noApp = true
        }
    }

    InlineSheet(onDismiss = onDismiss) {
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
                targetState = sentVia,
                label = "trustedContactSent",
                modifier = Modifier
                    .fillMaxWidth()
                    .animateContentSize()
            ) { via ->
                if (via == null) {
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
                            onClick = { send(smsIntent("$messageEn\n$messageHi"), "SMS") },
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 56.dp)
                                .semantics { contentDescription = "Send the question to $contactFirstName by SMS" }
                        ) {
                            Icon(Icons.Default.Sms, contentDescription = null, modifier = Modifier.size(24.dp))
                            Spacer(modifier = Modifier.width(12.dp))
                            BilingualLabel(en = "Send by SMS", hi = "SMS से भेजें")
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        OutlinedButton(
                            onClick = { send(whatsAppIntent("$messageEn\n$messageHi"), "WhatsApp") },
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 56.dp)
                                .semantics { contentDescription = "Send the question to $contactFirstName on WhatsApp" }
                        ) {
                            Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null, modifier = Modifier.size(24.dp))
                            Spacer(modifier = Modifier.width(12.dp))
                            BilingualLabel(en = "Send on WhatsApp", hi = "WhatsApp पर भेजें")
                        }

                        if (noApp) {
                            Spacer(modifier = Modifier.height(12.dp))
                            BilingualText(
                                en = "No messaging app found. Call $contactFirstName instead.",
                                hi = "कोई मैसेजिंग ऐप नहीं मिला। $contactFirstName को कॉल करें।",
                                style = MaterialTheme.typography.bodyMedium,
                                color = colors.error,
                                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
                            )
                        }
                    }
                } else {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .semantics { liveRegion = LiveRegionMode.Polite },
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.CheckCircle,
                            contentDescription = null,
                            tint = colors.tertiary,
                            modifier = Modifier.size(48.dp)
                        )
                        BilingualText(
                            en = "Message opened in $via. Wait for $contactFirstName's reply before you pay.",
                            hi = "संदेश $via में खुल गया। भुगतान से पहले $contactFirstName के जवाब का इंतज़ार करें।",
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
                        Button(
                            onClick = onDismiss,
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 56.dp)
                        ) {
                            BilingualLabel(en = "Back to the pause", hi = "विराम पर वापस जाएं")
                        }
                    }
                }
            }
        }
    }
}
