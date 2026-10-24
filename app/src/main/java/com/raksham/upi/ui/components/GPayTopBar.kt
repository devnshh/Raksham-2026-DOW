package com.raksham.upi.ui.components

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.BuildConfig
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.theme.*

@Composable
fun GPayTopBar(
    onScanQrClick: () -> Unit,
    onOpenLabClick: () -> Unit
) {
    val context = LocalContext.current
    val clipboardManager = LocalClipboardManager.current

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White)
            .statusBarsPadding()
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        // App Logo & Title Row:
        // Long-press on the app logo/title opens the Simulation Lab ONLY in debug mode!
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .pointerInput(Unit) {
                        detectTapGestures(
                            onLongPress = {
                                if (BuildConfig.DEBUG) {
                                    Toast.makeText(context, "🔧 Debug Mode: Launching Simulation Lab...", Toast.LENGTH_SHORT).show()
                                    onOpenLabClick()
                                }
                            }
                        )
                    }
                    .padding(vertical = 4.dp, horizontal = 2.dp)
            ) {
                // App Logo
                Surface(
                    modifier = Modifier.size(36.dp),
                    shape = RoundedCornerShape(10.dp),
                    color = GPayBlue
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = "₹",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }

                Spacer(modifier = Modifier.width(10.dp))

                Column {
                    Text(
                        text = "Raksham UPI",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "Instant & Secure Payments",
                        fontSize = 11.sp,
                        color = TextMuted
                    )
                }
            }

            // User Profile Avatar
            Surface(
                modifier = Modifier.size(38.dp),
                shape = CircleShape,
                color = GPayBlueLight
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = "U",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = GPayBlue
                    )
                }
            }
        }

        // Row with Search Bar and QR Scanner Action (Shield button removed: SDK is silent)
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Google Pay style search box
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .height(48.dp),
                shape = RoundedCornerShape(24.dp),
                color = SurfaceBackground,
                tonalElevation = 1.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Search,
                        contentDescription = "Search",
                        tint = TextSecondary,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "Pay friends and merchants",
                        color = TextMuted,
                        fontSize = 14.sp
                    )
                }
            }

            Spacer(modifier = Modifier.width(10.dp))

            // QR Scanner icon button
            IconButton(
                onClick = onScanQrClick,
                modifier = Modifier
                    .size(44.dp)
                    .background(SurfaceBackground, CircleShape)
            ) {
                Icon(
                    imageVector = Icons.Default.QrCodeScanner,
                    contentDescription = "Scan QR",
                    tint = TextPrimary,
                    modifier = Modifier.size(22.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // UPI ID Pill with 1-tap copy
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Start,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .clip(RoundedCornerShape(12.dp))
                    .background(GPayBlueLight.copy(alpha = 0.5f))
                    .clickable {
                        clipboardManager.setText(AnnotatedString(MockData.currentUserUpiId))
                        Toast.makeText(context, "UPI ID copied: ${MockData.currentUserUpiId}", Toast.LENGTH_SHORT).show()
                    }
                    .padding(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Text(
                    text = "UPI ID: ",
                    fontSize = 12.sp,
                    color = TextSecondary,
                    fontWeight = FontWeight.Normal
                )
                Text(
                    text = MockData.currentUserUpiId,
                    fontSize = 12.sp,
                    color = GPayBlue,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.width(6.dp))
                Icon(
                    imageVector = Icons.Default.ContentCopy,
                    contentDescription = "Copy",
                    tint = GPayBlue,
                    modifier = Modifier.size(13.dp)
                )
            }
        }
    }
}
