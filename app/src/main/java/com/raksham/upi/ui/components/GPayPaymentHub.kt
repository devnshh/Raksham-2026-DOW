package com.raksham.upi.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.ContactPhone
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.ui.theme.*

@Composable
fun GPayPaymentHub(
    onPayPhoneClick: () -> Unit,
    onPayUpiClick: () -> Unit,
    onScanQrClick: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(20.dp),
        color = Color.White,
        tonalElevation = 1.dp
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 16.dp, horizontal = 8.dp)
        ) {
            Text(
                text = "Transfer Money",
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextPrimary,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Exactly the 3 payment modes requested by user: Phone, UPI, QR
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                PaymentHubActionItem(
                    icon = Icons.Default.ContactPhone,
                    title = "Pay phone\nnumber",
                    iconColor = GPayBlue,
                    bgColor = GPayBlueLight,
                    onClick = onPayPhoneClick
                )

                PaymentHubActionItem(
                    icon = Icons.Default.AccountBalance,
                    title = "Pay UPI ID\nor VPA",
                    iconColor = Color(0xFF188038),
                    bgColor = GPayGreenLight,
                    onClick = onPayUpiClick
                )

                PaymentHubActionItem(
                    icon = Icons.Default.QrCodeScanner,
                    title = "Scan any\nQR code",
                    iconColor = Color(0xFFB06000),
                    bgColor = GPayYellowLight,
                    onClick = onScanQrClick
                )
            }
        }
    }
}

@Composable
private fun PaymentHubActionItem(
    icon: ImageVector,
    title: String,
    iconColor: Color,
    bgColor: Color,
    onClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(8.dp)
            .width(96.dp)
    ) {
        Box(
            modifier = Modifier
                .size(56.dp)
                .background(bgColor, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = title,
                tint = iconColor,
                modifier = Modifier.size(28.dp)
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = title,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            color = TextPrimary,
            textAlign = TextAlign.Center,
            lineHeight = 15.sp
        )
    }
}

