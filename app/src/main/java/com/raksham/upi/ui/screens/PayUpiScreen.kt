package com.raksham.upi.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.theme.*
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PayUpiScreen(
    onBackClick: () -> Unit,
    onProceedToAmount: (Contact) -> Unit
) {
    var upiInput by remember { mutableStateOf("") }
    val pspHandles = listOf("@oksbi", "@okaxis", "@okhdfcbank", "@paytm", "@ybl", "@ibl")

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Pay UPI ID or VPA", fontSize = 18.sp, fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        containerColor = SurfaceBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Spacer(modifier = Modifier.height(12.dp))

            // UPI ID Input Box
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = Color.White,
                tonalElevation = 1.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Enter any UPI ID (Virtual Payment Address)",
                        fontSize = 13.sp,
                        color = TextSecondary,
                        fontWeight = FontWeight.Medium
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedTextField(
                        value = upiInput,
                        onValueChange = { upiInput = it.lowercase().trim() },
                        placeholder = { Text("e.g. name@oksbi or merchant@ybl", color = TextMuted) },
                        singleLine = true,
                        leadingIcon = {
                            Icon(Icons.Default.AccountBalance, contentDescription = null, tint = GPayBlue)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    // Quick handle extension chips
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(pspHandles) { handle ->
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = SurfaceBackground,
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .clickable {
                                        val prefix = upiInput.substringBefore("@")
                                        upiInput = "$prefix$handle"
                                    }
                            ) {
                                Text(
                                    text = handle,
                                    fontSize = 12.sp,
                                    color = GPayBlue,
                                    fontWeight = FontWeight.Medium,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                                )
                            }
                        }
                    }

                    if (upiInput.contains("@") && upiInput.substringAfter("@").length >= 2) {
                        Spacer(modifier = Modifier.height(14.dp))
                        Button(
                            onClick = {
                                val cleanName = upiInput.substringBefore("@")
                                    .replace(".", " ")
                                    .replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
                                val contact = Contact(
                                    id = "upi_direct",
                                    name = cleanName,
                                    phone = "UPI Transfer",
                                    upiId = upiInput,
                                    avatarInitials = upiInput.take(2).uppercase(),
                                    colorHex = 0xFF1A73E8
                                )
                                onProceedToAmount(contact)
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = GPayBlue),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Verify & Pay to $upiInput", fontWeight = FontWeight.SemiBold)
                            Spacer(modifier = Modifier.width(6.dp))
                            Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // Sample Test Payees Section
            Text(
                text = "Sample Payees",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextPrimary
            )
            Text(
                text = "Select an account to test payment flow:",
                fontSize = 12.sp,
                color = TextMuted
            )

            Spacer(modifier = Modifier.height(8.dp))

            MockData.sampleScamPayees.forEach { sampleContact ->
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = Color.White,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .clickable { onProceedToAmount(sampleContact) }
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Surface(
                            modifier = Modifier.size(40.dp),
                            shape = CircleShape,
                            color = GPayBlueLight
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text(
                                    text = sampleContact.avatarInitials,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = GPayBlue
                                )
                            }
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = sampleContact.name,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Text(
                                text = sampleContact.upiId,
                                fontSize = 12.sp,
                                color = TextSecondary
                            )
                        }

                        Icon(
                            imageVector = Icons.Default.QrCode,
                            contentDescription = null,
                            tint = TextMuted,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}
