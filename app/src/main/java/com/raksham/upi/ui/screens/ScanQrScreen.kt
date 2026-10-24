package com.raksham.upi.ui.screens

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.FlashOn
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.raksham.upi.data.Contact
import com.raksham.upi.ui.theme.DarkColors
import com.raksham.upi.ui.theme.Motion

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanQrScreen(
    onBackClick: () -> Unit,
    onQrResolved: (contact: Contact, defaultAmount: Double?, entryChannel: String) -> Unit
) {
    // A camera screen is dark in both themes, like a stock scanner.
    MaterialTheme(colorScheme = DarkColors, typography = MaterialTheme.typography, shapes = MaterialTheme.shapes) {
        ScanQrContent(onBackClick, onQrResolved)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ScanQrContent(
    onBackClick: () -> Unit,
    onQrResolved: (contact: Contact, defaultAmount: Double?, entryChannel: String) -> Unit
) {
    var torchEnabled by remember { mutableStateOf(false) }

    // Scanner line sweeping the viewfinder
    val infiniteTransition = rememberInfiniteTransition(label = "laser")
    val laserOffsetY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 240f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = Motion.Emphasized),
            repeatMode = RepeatMode.Reverse
        ),
        label = "laser_y"
    )
    val torchTint by animateColorAsState(
        if (torchEnabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
        tween(Motion.SHORT),
        label = "torch tint"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan any UPI QR code") },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { torchEnabled = !torchEnabled }) {
                        Icon(
                            imageVector = Icons.Default.FlashOn,
                            contentDescription = "Flash",
                            tint = torchTint
                        )
                    }
                    IconButton(onClick = {
                        // Simulate selecting a QR code image received in WhatsApp chat (Family C: qr_gallery)
                        val galleryScamContact = Contact(
                            id = "gallery_qr",
                            name = "Power Rebate Officer",
                            phone = "QR received in WhatsApp",
                            upiId = "electricity-rebate@oksbi",
                            avatarInitials = "PR",
                            colorHex = 0xFFD93025
                        )
                        onQrResolved(galleryScamContact, 5000.0, "qr_gallery")
                    }) {
                        Icon(Icons.Default.Image, contentDescription = "Gallery")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Transparent,
                    scrolledContainerColor = Color.Transparent
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.surfaceContainerLowest
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.height(16.dp))

            Text(
                text = "Point your camera at a QR code to pay",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(Modifier.height(24.dp))

            Box(
                modifier = Modifier
                    .size(260.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(MaterialTheme.colorScheme.surfaceContainer)
                    .border(2.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(24.dp)),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(2.dp)
                        .offset(y = (laserOffsetY - 120).dp)
                        .background(
                            Brush.horizontalGradient(
                                listOf(Color.Transparent, MaterialTheme.colorScheme.primary, Color.Transparent)
                            )
                        )
                )

                Icon(
                    imageVector = Icons.Default.QrCode,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f),
                    modifier = Modifier.size(160.dp)
                )
            }

            Spacer(Modifier.height(32.dp))

            Text(
                text = "Demo QR codes",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "Tap a preset to test risk detection instantly",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 2.dp, bottom = 12.dp)
            )

            // Legit counter QR
            FilledTonalButton(
                onClick = {
                    val chaiContact = Contact(
                        id = "chai_qr",
                        name = "Chai Point Counter",
                        phone = "Merchant QR",
                        upiId = "chaipoint@icici",
                        avatarInitials = "CP",
                        colorHex = 0xFF137333,
                        isVerified = true
                    )
                    onQrResolved(chaiContact, 45.0, "qr_scan")
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
            ) {
                Text("Scan Chai Point QR (₹45 - Legit Merchant)", textAlign = TextAlign.Center)
            }

            Spacer(Modifier.height(8.dp))

            // Digital arrest QR
            FilledTonalButton(
                onClick = {
                    val policeScam = Contact(
                        id = "police_qr",
                        name = "CBI Cyber Cell Verification",
                        phone = "Scam Notice QR",
                        upiId = "cbi-verification-dept@ybl",
                        avatarInitials = "CB",
                        colorHex = 0xFFD93025
                    )
                    onQrResolved(policeScam, 48000.0, "qr_scan")
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
            ) {
                Text("Scan Fake CBI Notice QR (₹48,000 - Scam)", textAlign = TextAlign.Center)
            }

            Spacer(Modifier.height(8.dp))

            // WhatsApp QR from gallery
            FilledTonalButton(
                onClick = {
                    val galleryMule = Contact(
                        id = "rebate_qr",
                        name = "Govt Rebate Officer",
                        phone = "QR from WhatsApp",
                        upiId = "electricity-rebate@oksbi",
                        avatarInitials = "RE",
                        colorHex = 0xFFD93025
                    )
                    onQrResolved(galleryMule, 5000.0, "qr_gallery")
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
            ) {
                Text("Import Fake Rebate QR from Chat (₹5,000)", textAlign = TextAlign.Center)
            }

            Spacer(Modifier.height(24.dp))
        }
    }
}
