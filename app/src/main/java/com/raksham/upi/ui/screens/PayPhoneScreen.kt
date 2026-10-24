package com.raksham.upi.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.theme.Motion

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun PayPhoneScreen(
    onBackClick: () -> Unit,
    onContactSelected: (Contact) -> Unit
) {
    var phoneNumber by remember { mutableStateOf("") }

    val filteredContacts = remember(phoneNumber) {
        if (phoneNumber.isBlank()) {
            MockData.contacts
        } else {
            MockData.contacts.filter {
                it.phone.contains(phoneNumber) || it.name.contains(phoneNumber, ignoreCase = true)
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Pay phone number") },
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
        ) {
            TextField(
                value = phoneNumber,
                onValueChange = { if (it.length <= 10) phoneNumber = it },
                placeholder = { Text("Enter phone number or name") },
                leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null) },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                singleLine = true,
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

            AnimatedVisibility(
                visible = phoneNumber.length == 10,
                enter = expandVertically(tween(Motion.MEDIUM, easing = Motion.EmphasizedDecelerate)) + fadeIn(tween(Motion.MEDIUM)),
                exit = shrinkVertically(tween(Motion.SHORT, easing = Motion.EmphasizedAccelerate)) + fadeOut(tween(Motion.SHORT))
            ) {
                Button(
                    onClick = {
                        val customContact = Contact(
                            id = "custom_phone",
                            name = "+91 $phoneNumber",
                            phone = "+91 $phoneNumber",
                            upiId = "$phoneNumber@oksbi",
                            avatarInitials = "P",
                            colorHex = 0xFF1A73E8
                        )
                        onContactSelected(customContact)
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                        .heightIn(min = 48.dp)
                ) {
                    Text("Pay to +91 $phoneNumber")
                    Spacer(Modifier.width(8.dp))
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(18.dp))
                }
            }

            Text(
                "Recent contacts",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 4.dp)
            )

            LazyColumn(modifier = Modifier.fillMaxWidth().weight(1f)) {
                items(filteredContacts, key = { it.id }) { contact ->
                    ListItem(
                        leadingContent = {
                            Box(
                                contentAlignment = Alignment.Center,
                                modifier = Modifier.size(40.dp).background(Color(contact.colorHex), CircleShape)
                            ) {
                                Text(contact.avatarInitials, color = Color.White, style = MaterialTheme.typography.titleMedium)
                            }
                        },
                        headlineContent = { Text(contact.name, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                        supportingContent = {
                            Text("${contact.phone} · ${contact.upiId}", maxLines = 1, overflow = TextOverflow.Ellipsis)
                        },
                        modifier = Modifier
                            .animateItemPlacement(tween(Motion.MEDIUM, easing = Motion.Emphasized))
                            .clickable { onContactSelected(contact) }
                    )
                }
            }
        }
    }
}
