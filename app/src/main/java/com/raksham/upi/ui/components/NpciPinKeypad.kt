package com.raksham.upi.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Backspace
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.data.BankAccount
import com.raksham.upi.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NpciPinBottomSheet(
    payeeName: String,
    amount: Double,
    bankAccount: BankAccount,
    onPinSuccess: () -> Unit,
    onDismiss: () -> Unit
) {
    var enteredPin by remember { mutableStateOf("") }
    val pinLength = 6
    var pinStartTime by remember { mutableLongStateOf(System.currentTimeMillis()) }

    ModalBottomSheet(
        onDismissRequest = {
            onDismiss()
        },
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = Color.White,
        shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 32.dp, start = 20.dp, end = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // NPCI Brand Strip
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Lock,
                        contentDescription = "Secure",
                        tint = GPayBlue,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "UPI Secure PIN",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = GPayBlue
                    )
                }

                Text(
                    text = "NPCI Unified Platform",
                    fontSize = 11.sp,
                    color = TextMuted,
                    fontWeight = FontWeight.Medium
                )
            }

            HorizontalDivider(color = DividerColor, thickness = 1.dp)

            Spacer(modifier = Modifier.height(16.dp))

            // Transaction Summary Strip
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(text = "Paying", fontSize = 12.sp, color = TextMuted)
                    Text(text = payeeName, fontSize = 15.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    Text(text = "${bankAccount.bankName} ${bankAccount.accountNumberMasked}", fontSize = 11.sp, color = TextSecondary)
                }

                Text(
                    text = "₹${String.format("%,.0f", amount)}",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = TextPrimary
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "ENTER 6-DIGIT UPI PIN",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = TextSecondary,
                letterSpacing = 1.sp
            )

            Spacer(modifier = Modifier.height(14.dp))

            // PIN Dot Indicators
            Row(
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                for (i in 0 until pinLength) {
                    val isFilled = i < enteredPin.length
                    Box(
                        modifier = Modifier
                            .size(16.dp)
                            .background(
                                color = if (isFilled) GPayBlue else Color(0xFFE2E8F0),
                                shape = CircleShape
                            )
                    )
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Keypad Layout (1-9, Backspace, 0, Submit)
            val keys = listOf(
                listOf("1", "2", "3"),
                listOf("4", "5", "6"),
                listOf("7", "8", "9"),
                listOf("backspace", "0", "check")
            )

            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                keys.forEach { rowKeys ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        rowKeys.forEach { key ->
                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = if (key == "check") GPayBlue else SurfaceBackground,
                                modifier = Modifier
                                    .weight(1f)
                                    .height(52.dp)
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable {
                                        when (key) {
                                            "backspace" -> {
                                                if (enteredPin.isNotEmpty()) {
                                                    enteredPin = enteredPin.dropLast(1)
                                                }
                                            }
                                            "check" -> {
                                                if (enteredPin.length == pinLength) {
                                                    onPinSuccess()
                                                }
                                            }
                                            else -> {
                                                if (enteredPin.length < pinLength) {
                                                    enteredPin += key
                                                    if (enteredPin.length == pinLength) {
                                                        onPinSuccess()
                                                    }
                                                }
                                            }
                                        }
                                    }
                            ) {
                                Box(
                                    modifier = Modifier.fillMaxSize(),
                                    contentAlignment = Alignment.Center
                                ) {
                                    when (key) {
                                        "backspace" -> Icon(
                                            imageVector = Icons.AutoMirrored.Filled.Backspace,
                                            contentDescription = "Delete",
                                            tint = TextPrimary,
                                            modifier = Modifier.size(20.dp)
                                        )
                                        "check" -> Icon(
                                            imageVector = Icons.Default.Check,
                                            contentDescription = "Submit",
                                            tint = Color.White,
                                            modifier = Modifier.size(24.dp)
                                        )
                                        else -> Text(
                                            text = key,
                                            fontSize = 20.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = TextPrimary
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
