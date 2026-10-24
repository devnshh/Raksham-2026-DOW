package com.raksham.upi.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.ui.theme.*
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

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
        containerColor = Color.White
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(54.dp)
                    .background(GPayBlueLight, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Person,
                    contentDescription = "Trusted Contact",
                    tint = GPayBlue,
                    modifier = Modifier.size(30.dp)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Ask $contactFirstName (Trusted Contact)",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary,
                textAlign = TextAlign.Center
            )

            Text(
                text = "विश्वसनीय संपर्क से पुष्टि करें",
                fontSize = 14.sp,
                color = TextMuted,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            when (status) {
                TrustedContactStatus.IDLE -> {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = SurfaceBackground,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Text(
                                text = "Message Preview:",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TextSecondary
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "\"$messageEn\"",
                                fontSize = 14.sp,
                                color = TextPrimary,
                                fontWeight = FontWeight.Medium
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "\"$messageHi\"",
                                fontSize = 13.sp,
                                color = TextSecondary
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = { status = TrustedContactStatus.WAITING },
                        colors = ButtonDefaults.buttonColors(containerColor = GPayBlue),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                            .semantics { contentDescription = "Send verification request to $contactFirstName" }
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Send Verification Request", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    }
                }

                TrustedContactStatus.WAITING -> {
                    CircularProgressIndicator(
                        color = GPayBlue,
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Waiting for $contactFirstName's response...",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary
                    )
                    Text(
                        text = "$contactFirstName के उत्तर की प्रतीक्षा की जा रही है...",
                        fontSize = 13.sp,
                        color = TextMuted
                    )
                }

                TrustedContactStatus.APPROVED -> {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = "Approved",
                        tint = GPayGreen,
                        modifier = Modifier.size(40.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "$contactFirstName responded: Payment looks okay.",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = GPayGreen
                    )
                    Text(
                        text = "Note: Safety hold countdown is still running.",
                        fontSize = 12.sp,
                        color = TextMuted
                    )
                }

                TrustedContactStatus.DECLINED -> {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Declined",
                        tint = GPayRed,
                        modifier = Modifier.size(40.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "$contactFirstName warned: Do not proceed! Suspected scam.",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = GPayRed,
                        textAlign = TextAlign.Center
                    )
                    Text(
                        text = "$contactFirstName ने सलाह दी है कि यह धोखाधड़ी हो सकती है। भुगतान रद्द किया गया।",
                        fontSize = 13.sp,
                        color = TextMuted,
                        textAlign = TextAlign.Center
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}
