package com.raksham.upi.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.components.*
import com.raksham.upi.ui.theme.SurfaceBackground

@Composable
fun GPayHomeScreen(
    onPayPhoneClick: () -> Unit,
    onPayUpiClick: () -> Unit,
    onScanQrClick: () -> Unit,
    onSelectContact: (Contact) -> Unit,
    onOpenLabClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(SurfaceBackground)
            .verticalScroll(rememberScrollState())
    ) {
        // Google Pay Top Bar with Search & User UPI ID
        GPayTopBar(
            onScanQrClick = onScanQrClick,
            onOpenLabClick = onOpenLabClick
        )

        Spacer(modifier = Modifier.height(6.dp))

        // Google Pay Payment Action Hub (strictly Phone, UPI, QR as requested)
        GPayPaymentHub(
            onPayPhoneClick = onPayPhoneClick,
            onPayUpiClick = onPayUpiClick,
            onScanQrClick = onScanQrClick
        )

        Spacer(modifier = Modifier.height(4.dp))

        // People & Contacts Carousel
        GPayPeopleSection(
            contacts = MockData.contacts,
            onContactClick = onSelectContact
        )

        Spacer(modifier = Modifier.height(4.dp))

        // Recent Transactions List
        GPayTransactionsList(
            transactions = MockData.recentTransactions
        )

        Spacer(modifier = Modifier.height(24.dp))
    }
}

