package com.raksham.upi.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.raksham.risk.session.SessionSignals
import com.raksham.upi.data.Contact
import java.util.Locale

/** Entry channels a judge can pick, as the risk check names them. */
private val CHANNELS = listOf("typed_vpa" to "Typed", "qr_scan" to "QR", "deep_link_sms" to "Link")

/**
 * Any payee, amount, entry channel and session state, run through the real risk check and the real
 * warning screens. The toggles replace what the phone would measure, for this one payment only.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomScenarioCard(
    onOpen: (contact: Contact, amount: Double, entryChannel: String, note: String, signals: SessionSignals) -> Unit
) {
    var upi by remember { mutableStateOf("") }
    var amountText by remember { mutableStateOf("") }
    var channel by remember { mutableStateOf(CHANNELS.first().first) }
    var onCall by remember { mutableStateOf(false) }
    var callerSaved by remember { mutableStateOf(false) }
    var screenShared by remember { mutableStateOf(false) }
    var remoteNew by remember { mutableStateOf(false) }
    var note by remember { mutableStateOf("") }

    val amount = amountText.toDoubleOrNull()
    val vpa = upi.trim().lowercase()
    val upiValid = vpa.contains("@") && vpa.substringAfter("@").length >= 2
    val canOpen = upiValid && amount != null && amount > 0

    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        OutlinedTextField(
            value = upi,
            onValueChange = { upi = it },
            label = { Text("Payee UPI ID") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = amountText,
            onValueChange = { v -> amountText = v.filter { it.isDigit() || it == '.' } },
            label = { Text("Amount (₹)") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth()
        )
        Text("Entered by", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
            CHANNELS.forEachIndexed { i, (code, label) ->
                SegmentedButton(
                    selected = channel == code,
                    onClick = { channel = code },
                    shape = SegmentedButtonDefaults.itemShape(i, CHANNELS.size)
                ) { Text(label) }
            }
        }
        SignalSwitch("On a call", onCall) { onCall = it }
        if (onCall) SignalSwitch("Caller is a saved contact", callerSaved) { callerSaved = it }
        SignalSwitch("Screen shared", screenShared) { screenShared = it }
        SignalSwitch("New remote-access app", remoteNew) { remoteNew = it }
        OutlinedTextField(
            value = note,
            onValueChange = { note = it },
            label = { Text("Note (optional)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )
        Button(
            onClick = {
                val name = vpa.substringBefore("@").replace(".", " ").replace("-", " ")
                    .replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
                val contact = Contact("custom", name, "Custom scenario", vpa, vpa.take(2).uppercase(), 0xFF1A73E8)
                onOpen(
                    contact, amount!!, channel, note,
                    SessionSignals(
                        on_call = onCall,
                        caller_in_contacts = if (onCall) callerSaved else null,
                        screen_shared = screenShared,
                        remote_app_present = remoteNew,
                        remote_app_new = remoteNew
                    )
                )
            },
            enabled = canOpen,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
        ) { Text("Open in the payment screen") }
        Text(
            "Tap Pay there to see the real amber, red or decline screen. The toggles apply to this payment only.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun SignalSwitch(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .toggleable(value = checked, role = Role.Switch, onValueChange = onChange),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Switch(checked = checked, onCheckedChange = null)
    }
}
