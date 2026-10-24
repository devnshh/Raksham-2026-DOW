package com.raksham.upi.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.raksham.risk.model.RiskDecision
import com.raksham.upi.ui.templates.TemplateRegistry
import com.raksham.upi.ui.theme.*

@Composable
fun AmberWarningDialog(
    decision: RiskDecision,
    payeeName: String = "",
    amount: Double = 0.0,
    onContinue: () -> Unit,
    onCancel: () -> Unit
) {
    val template = TemplateRegistry.resolve(decision.templateId)
    val reasonsToShow = decision.reasons.take(3)

    Dialog(
        onDismissRequest = onCancel,
        properties = DialogProperties(dismissOnBackPress = true, dismissOnClickOutside = false)
    ) {
        Surface(
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .padding(vertical = 16.dp),
            shape = RoundedCornerShape(24.dp),
            color = Color.White,
            tonalElevation = 6.dp
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(22.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Warning Icon Badge
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .background(GPayYellowLight, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = "Caution Notice",
                        tint = AlertAmber,
                        modifier = Modifier.size(32.dp)
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Title (English)
                Text(
                    text = template.titleEn,
                    fontSize = 19.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary,
                    textAlign = TextAlign.Center
                )

                // Title (Hindi)
                Text(
                    text = template.titleHi,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = TextMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 2.dp)
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Explanation Body (English + Hindi)
                Text(
                    text = template.bodyEn,
                    fontSize = 16.sp,
                    color = TextSecondary,
                    lineHeight = 22.sp,
                    textAlign = TextAlign.Center
                )

                Text(
                    text = template.bodyHi,
                    fontSize = 14.sp,
                    color = TextMuted,
                    lineHeight = 20.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 4.dp)
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Reason items (up to 3, one line each, with English and Hindi)
                if (reasonsToShow.isNotEmpty() && !decision.isCheckUnavailable) {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        reasonsToShow.forEach { r ->
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = SurfaceBackground,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                                    Text(
                                        text = "• ${r.en}",
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TextPrimary
                                    )
                                    Text(
                                        text = "  ${r.hi}",
                                        fontSize = 12.sp,
                                        color = TextMuted
                                    )
                                }
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(20.dp))
                } else {
                    Spacer(modifier = Modifier.height(12.dp))
                }

                // Actions: Cancel payment (Primary) and Continue anyway (Secondary)
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Primary: Cancel payment
                    Button(
                        onClick = onCancel,
                        colors = ButtonDefaults.buttonColors(containerColor = GPayRed),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                            .semantics { contentDescription = "Cancel payment" }
                    ) {
                        Text(
                            text = "Cancel Payment",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }

                    // Secondary: Continue anyway (single tap, no extra confirmation)
                    OutlinedButton(
                        onClick = onContinue,
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                            .semantics { contentDescription = "Continue anyway" }
                    ) {
                        Text(
                            text = "Continue anyway",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextSecondary
                        )
                    }
                }
            }
        }
    }
}
