package com.raksham.upi.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.outlined.AlternateEmail
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.theme.Motion
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
                title = { Text("Pay UPI ID") },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .consumeWindowInsets(padding)
                .imePadding()
                .verticalScroll(rememberScrollState())
        ) {
            TextField(
                value = upiInput,
                onValueChange = { upiInput = it.lowercase().trim() },
                placeholder = { Text("name@bank") },
                supportingText = { Text("Enter any UPI ID (virtual payment address)") },
                singleLine = true,
                leadingIcon = { Icon(Icons.Outlined.AlternateEmail, contentDescription = null) },
                shape = CircleShape,
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .heightIn(min = 56.dp)
            )

            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(horizontal = 16.dp)
            ) {
                items(pspHandles) { handle ->
                    AssistChip(
                        onClick = {
                            val prefix = upiInput.substringBefore("@")
                            upiInput = "$prefix$handle"
                        },
                        label = { Text(handle) },
                        shape = CircleShape
                    )
                }
            }

            AnimatedVisibility(
                visible = upiInput.contains("@") && upiInput.substringAfter("@").length >= 2,
                enter = expandVertically(tween(Motion.MEDIUM, easing = Motion.EmphasizedDecelerate)) + fadeIn(tween(Motion.MEDIUM)),
                exit = shrinkVertically(tween(Motion.SHORT, easing = Motion.EmphasizedAccelerate)) + fadeOut(tween(Motion.SHORT))
            ) {
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
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(start = 16.dp, end = 16.dp, top = 16.dp)
                        .heightIn(min = 48.dp)
                ) {
                    Text("Verify and pay $upiInput", maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f, fill = false))
                    Spacer(Modifier.width(8.dp))
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(18.dp))
                }
            }

            Text(
                "Sample payees",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp)
            )
            Text(
                "Pick one to try the payment flow",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, bottom = 4.dp)
            )

            MockData.sampleScamPayees.forEach { sampleContact ->
                ListItem(
                    leadingContent = {
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.primaryContainer, CircleShape)
                        ) {
                            Text(
                                sampleContact.avatarInitials,
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                style = MaterialTheme.typography.titleMedium
                            )
                        }
                    },
                    headlineContent = { Text(sampleContact.name, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                    supportingContent = { Text(sampleContact.upiId, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                    modifier = Modifier.clickable { onProceedToAmount(sampleContact) }
                )
            }

            Spacer(Modifier.height(24.dp))
        }
    }
}
