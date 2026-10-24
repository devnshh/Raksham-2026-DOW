package com.raksham.upi.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.data.Contact
import com.raksham.upi.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanQrScreen(
    onBackClick: () -> Unit,
    onQrResolved: (contact: Contact, defaultAmount: Double?, entryChannel: String) -> Unit
) {
    var torchEnabled by remember { mutableStateOf(false) }

    // Animated scanner laser beam moving up and down
    val infiniteTransition = rememberInfiniteTransition(label = "laser")
    val laserOffsetY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 240f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "laser_y"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan any UPI QR Code", fontSize = 18.sp, color = Color.White) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                actions = {
                    IconButton(onClick = { torchEnabled = !torchEnabled }) {
                        Icon(
                            imageVector = Icons.Default.FlashOn,
                            contentDescription = "Flash",
                            tint = if (torchEnabled) GPayYellow else Color.White
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
                        Icon(Icons.Default.Image, contentDescription = "Gallery", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Black)
            )
        },
        containerColor = Color.Black
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "Point camera at any QR code to pay",
                color = Color.White.copy(alpha = 0.8f),
                fontSize = 14.sp
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Camera Viewfinder Box with Laser Animation
            Box(
                modifier = Modifier
                    .size(260.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(Color(0xFF111827))
                    .border(2.dp, Color(0xFF38BDF8), RoundedCornerShape(24.dp)),
                contentAlignment = Alignment.Center
            ) {
                // Moving laser scanner line
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .offset(y = (laserOffsetY - 120).dp)
                        .background(
                            Brush.horizontalGradient(
                                listOf(Color.Transparent, Color(0xFF00E5FF), Color(0xFF38BDF8), Color.Transparent)
                            )
                        )
                )

                Icon(
                    imageVector = Icons.Default.QrCode,
                    contentDescription = null,
                    tint = Color.White.copy(alpha = 0.15f),
                    modifier = Modifier.size(160.dp)
                )
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Quick Interactive QR Simulator Chips (for test & demo)
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp),
                shape = RoundedCornerShape(16.dp),
                color = Color(0xFF1E293B)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "⚡ Quick QR Test Simulations",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF38BDF8)
                    )
                    Text(
                        text = "Tap a preset QR to test risk feature extraction instantly:",
                        fontSize = 11.sp,
                        color = Color(0xFF94A3B8),
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = 2.dp, bottom = 12.dp)
                    )

                    // Button 1: Chai Point (Legit Counter QR)
                    Button(
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
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF065F46)),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Scan Chai Point QR (₹45 - Legit Merchant)", fontSize = 12.sp, color = Color(0xFFA7F3D0))
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Button 2: Digital Arrest QR
                    Button(
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
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF991B1B)),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Scan Fake CBI Notice QR (₹48,000 - Scam)", fontSize = 12.sp, color = Color(0xFFFECACA))
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Button 3: WhatsApp QR Gallery
                    Button(
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
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF7C2D12)),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Import Fake Rebate QR from Chat (₹5,000)", fontSize = 12.sp, color = Color(0xFFFED7AA))
                    }
                }
            }
        }
    }
}

