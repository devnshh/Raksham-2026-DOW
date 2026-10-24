package com.raksham.upi.ui.screens

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.CurrencyRupee
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.AlternateEmail
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.CurrencyRupee
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.NorthEast
import androidx.compose.material.icons.outlined.PersonAddAlt
import androidx.compose.material.icons.outlined.PhoneAndroid
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Science
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.SouthWest
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.raksham.upi.BuildConfig
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.data.TransactionItem
import com.raksham.upi.ui.theme.Motion
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.util.Locale

// The host app mirrors a stock UPI app's home; Satark itself only appears when it interrupts a payment.

private enum class HomeTab(val label: String, val selected: ImageVector, val unselected: ImageVector) {
    Home("Home", Icons.Filled.Home, Icons.Outlined.Home),
    Money("Money", Icons.Filled.CurrencyRupee, Icons.Outlined.CurrencyRupee),
    You("You", Icons.Filled.AccountCircle, Icons.Outlined.AccountCircle)
}

@Composable
fun HomeScreen(
    onPayPhoneClick: () -> Unit,
    onPayUpiClick: () -> Unit,
    onScanQrClick: () -> Unit,
    onSelectContact: (Contact) -> Unit,
    onOpenLabClick: () -> Unit
) {
    var tab by rememberSaveable { mutableStateOf(HomeTab.Home) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current
    val homeList = rememberLazyListState()
    val fabExpanded by remember { derivedStateOf { homeList.firstVisibleItemIndex == 0 } }

    fun showMessage(text: String) {
        scope.launch {
            snackbar.currentSnackbarData?.dismiss()
            snackbar.showSnackbar(text)
        }
    }
    val copyUpiId = {
        clipboard.setText(AnnotatedString(MockData.currentUserUpiId))
        showMessage("UPI ID copied")
    }
    val notInDemo = { showMessage("Not available in this demo") }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        floatingActionButton = {
            AnimatedVisibility(
                visible = tab == HomeTab.Home,
                enter = scaleIn(tween(Motion.MEDIUM, easing = Motion.EmphasizedDecelerate)) + fadeIn(),
                exit = scaleOut(tween(Motion.SHORT, easing = Motion.EmphasizedAccelerate)) + fadeOut()
            ) {
                ExtendedFloatingActionButton(
                    text = { Text("Scan QR") },
                    icon = { Icon(Icons.Outlined.QrCodeScanner, contentDescription = null) },
                    onClick = onScanQrClick,
                    expanded = fabExpanded,
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        },
        bottomBar = {
            NavigationBar {
                HomeTab.entries.forEach { item ->
                    NavigationBarItem(
                        selected = tab == item,
                        onClick = { tab = item },
                        icon = { Icon(if (tab == item) item.selected else item.unselected, contentDescription = null) },
                        label = { Text(item.label) }
                    )
                }
            }
        }
    ) { padding ->
        // Fade-through between tabs: outgoing fades fast, incoming fades and settles from 92 %.
        AnimatedContent(
            targetState = tab,
            transitionSpec = {
                (fadeIn(tween(210, delayMillis = 90, easing = Motion.EmphasizedDecelerate)) +
                    scaleIn(tween(210, delayMillis = 90, easing = Motion.EmphasizedDecelerate), initialScale = 0.92f))
                    .togetherWith(fadeOut(tween(90)))
            },
            label = "home tabs"
        ) { current ->
            when (current) {
                HomeTab.Home -> HomeTabContent(
                    padding = padding,
                    listState = homeList,
                    onSearchClick = onPayUpiClick,
                    onAvatarClick = { tab = HomeTab.You },
                    onScanQrClick = onScanQrClick,
                    onPayPhoneClick = onPayPhoneClick,
                    onPayUpiClick = onPayUpiClick,
                    onCopyUpiId = copyUpiId,
                    onNotInDemo = notInDemo,
                    onSelectContact = onSelectContact,
                    onHistoryClick = { tab = HomeTab.Money },
                    onBankAccountsClick = { tab = HomeTab.You }
                )
                HomeTab.Money -> MoneyTabContent(padding)
                HomeTab.You -> YouTabContent(padding, onCopyUpiId = copyUpiId, onOpenLabClick = onOpenLabClick)
            }
        }
    }
}

@Composable
private fun HomeTabContent(
    padding: PaddingValues,
    listState: LazyListState,
    onSearchClick: () -> Unit,
    onAvatarClick: () -> Unit,
    onScanQrClick: () -> Unit,
    onPayPhoneClick: () -> Unit,
    onPayUpiClick: () -> Unit,
    onCopyUpiId: () -> Unit,
    onNotInDemo: () -> Unit,
    onSelectContact: (Contact) -> Unit,
    onHistoryClick: () -> Unit,
    onBankAccountsClick: () -> Unit
) {
    LazyColumn(
        state = listState,
        contentPadding = PaddingValues(top = padding.calculateTopPadding() + 8.dp, bottom = padding.calculateBottomPadding() + 96.dp),
        modifier = Modifier.fillMaxSize()
    ) {
        item {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(horizontal = 16.dp)
            ) {
                Surface(
                    onClick = onSearchClick,
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surfaceContainerHigh,
                    modifier = Modifier.weight(1f).height(56.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(horizontal = 20.dp)) {
                        Icon(Icons.Outlined.Search, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.width(16.dp))
                        Text(
                            "Pay anyone on UPI",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Spacer(Modifier.width(12.dp))
                Avatar(
                    initials = "U",
                    color = MaterialTheme.colorScheme.primaryContainer,
                    textColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    size = 48,
                    modifier = Modifier.clip(CircleShape).clickable(role = Role.Button, onClickLabel = "Open your profile", onClick = onAvatarClick)
                )
            }
        }

        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 28.dp)
            ) {
                ActionTile(Icons.Outlined.QrCodeScanner, "Scan any\nQR code", onScanQrClick, Modifier.weight(1f))
                ActionTile(Icons.Outlined.PersonAddAlt, "Pay\nanyone", onPayPhoneClick, Modifier.weight(1f))
                ActionTile(Icons.Outlined.AlternateEmail, "Pay\nUPI ID", onPayUpiClick, Modifier.weight(1f))
                ActionTile(Icons.Outlined.PhoneAndroid, "Mobile\nrecharge", onNotInDemo, Modifier.weight(1f))
            }
        }

        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(top = 16.dp).horizontalScroll(rememberScrollState()).padding(horizontal = 16.dp)
            ) {
                ShortcutPill("UPI Lite", onClick = onNotInDemo)
                ShortcutPill("Rewards", onClick = onNotInDemo)
                ShortcutPill("UPI ID: ${MockData.currentUserUpiId}", onClick = onCopyUpiId, icon = Icons.Outlined.ContentCopy)
            }
        }

        item { SectionTitle("Send money", Modifier.padding(top = 32.dp, bottom = 8.dp)) }

        item {
            // Seven people and a "More" cell, four per row.
            val cells: List<Contact?> = MockData.contacts.take(7) + null
            Column(verticalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.padding(horizontal = 8.dp)) {
                cells.chunked(4).forEach { row ->
                    Row {
                        row.forEach { contact ->
                            if (contact != null) {
                                PersonCell(contact.name.substringBefore(" "), onClick = { onSelectContact(contact) }, Modifier.weight(1f)) {
                                    Avatar(contact.avatarInitials, Color(contact.colorHex), Color.White, size = 56)
                                }
                            } else {
                                PersonCell("More", onClick = onPayPhoneClick, Modifier.weight(1f)) {
                                    Box(
                                        contentAlignment = Alignment.Center,
                                        modifier = Modifier.size(56.dp).background(MaterialTheme.colorScheme.surfaceContainerHigh, CircleShape)
                                    ) { Icon(Icons.Outlined.ExpandMore, contentDescription = null) }
                                }
                            }
                        }
                    }
                }
            }
        }

        item { SectionTitle("Manage your money", Modifier.padding(top = 32.dp, bottom = 4.dp)) }
        item { LinkRow(Icons.AutoMirrored.Outlined.ReceiptLong, "See transaction history", onHistoryClick) }
        item { LinkRow(Icons.Outlined.AccountBalance, "Your bank accounts", onBankAccountsClick) }
    }
}

@Composable
private fun MoneyTabContent(padding: PaddingValues) {
    LazyColumn(contentPadding = padding, modifier = Modifier.fillMaxSize()) {
        item {
            Text(
                "Transaction history",
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 12.dp)
            )
        }
        items(MockData.recentTransactions, key = { it.id }) { TransactionRow(it) }
    }
}

@Composable
private fun YouTabContent(padding: PaddingValues, onCopyUpiId: () -> Unit, onOpenLabClick: () -> Unit) {
    LazyColumn(contentPadding = padding, modifier = Modifier.fillMaxSize()) {
        item {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth().padding(top = 32.dp, bottom = 16.dp)
            ) {
                Avatar("U", MaterialTheme.colorScheme.primaryContainer, MaterialTheme.colorScheme.onPrimaryContainer, size = 88)
                Spacer(Modifier.height(16.dp))
                Text(MockData.currentUserName.removeSuffix(" (You)"), style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(12.dp))
                ShortcutPill("UPI ID: ${MockData.currentUserUpiId}", onClick = onCopyUpiId, icon = Icons.Outlined.ContentCopy)
            }
        }
        item { SectionTitle("Bank accounts", Modifier.padding(top = 16.dp, bottom = 4.dp)) }
        items(MockData.linkedBankAccounts, key = { it.id }) { account ->
            ListItem(
                leadingContent = { IconBadge(Icons.Outlined.AccountBalance) },
                headlineContent = { Text(account.bankName) },
                supportingContent = { Text("${account.accountType} ${account.accountNumberMasked}") },
                trailingContent = if (account.isPrimary) {
                    { Text("Primary", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary) }
                } else null
            )
        }
        if (BuildConfig.DEBUG) {
            item { SectionTitle("Demo tools", Modifier.padding(top = 16.dp, bottom = 4.dp)) }
            item {
                ListItem(
                    leadingContent = { IconBadge(Icons.Outlined.Science) },
                    headlineContent = { Text("Satark Simulation Lab") },
                    supportingContent = { Text("Scripted scam scenarios and the Risk API address") },
                    modifier = Modifier.clickable(onClick = onOpenLabClick)
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.titleMedium, modifier = modifier.padding(horizontal = 16.dp))
}

@Composable
private fun ActionTile(icon: ImageVector, label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier.clip(MaterialTheme.shapes.medium).clickable(role = Role.Button, onClick = onClick)
    ) {
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = MaterialTheme.colorScheme.primaryContainer,
            modifier = Modifier.fillMaxWidth().aspectRatio(1.1f)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer, modifier = Modifier.size(28.dp))
            }
        }
        Spacer(Modifier.height(8.dp))
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            minLines = 2,
            maxLines = 2,
            modifier = Modifier.padding(bottom = 4.dp)
        )
    }
}

@Composable
private fun ShortcutPill(label: String, onClick: () -> Unit, icon: ImageVector? = null) {
    Surface(
        onClick = onClick,
        shape = CircleShape,
        color = MaterialTheme.colorScheme.surfaceContainerHigh,
        modifier = Modifier.heightIn(min = 40.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
            Text(label, style = MaterialTheme.typography.labelLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (icon != null) {
                Spacer(Modifier.width(8.dp))
                Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
            }
        }
    }
}

@Composable
private fun PersonCell(label: String, onClick: () -> Unit, modifier: Modifier = Modifier, avatar: @Composable () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .clip(MaterialTheme.shapes.medium)
            .clickable(role = Role.Button, onClick = onClick)
            .padding(vertical = 8.dp)
    ) {
        avatar()
        Spacer(Modifier.height(8.dp))
        Text(label, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun LinkRow(icon: ImageVector, label: String, onClick: () -> Unit) {
    ListItem(
        leadingContent = { IconBadge(icon) },
        headlineContent = { Text(label) },
        trailingContent = { Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null) },
        modifier = Modifier.clickable(onClick = onClick)
    )
}

@Composable
private fun IconBadge(icon: ImageVector) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.surfaceContainerHigh, CircleShape)
    ) { Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp)) }
}

@Composable
private fun Avatar(initials: String, color: Color, textColor: Color, size: Int, modifier: Modifier = Modifier) {
    Box(contentAlignment = Alignment.Center, modifier = modifier.size(size.dp).background(color, CircleShape)) {
        Text(
            initials,
            color = textColor,
            style = if (size >= 72) MaterialTheme.typography.headlineMedium else MaterialTheme.typography.titleMedium
        )
    }
}

private val Rupees: NumberFormat = NumberFormat.getNumberInstance(Locale("en", "IN"))

@Composable
private fun TransactionRow(txn: TransactionItem) {
    ListItem(
        leadingContent = {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(40.dp)
                    .background(
                        if (txn.isCredit) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                        CircleShape
                    )
            ) {
                Icon(
                    if (txn.isCredit) Icons.Outlined.SouthWest else Icons.Outlined.NorthEast,
                    contentDescription = if (txn.isCredit) "Received" else "Paid",
                    tint = if (txn.isCredit) MaterialTheme.colorScheme.onTertiaryContainer else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
            }
        },
        headlineContent = { Text(txn.title, maxLines = 1, overflow = TextOverflow.Ellipsis) },
        supportingContent = { Text("${txn.subtitle} · ${txn.dateString}", maxLines = 1, overflow = TextOverflow.Ellipsis) },
        trailingContent = {
            Text(
                (if (txn.isCredit) "+₹" else "₹") + Rupees.format(txn.amount),
                style = MaterialTheme.typography.titleMedium,
                color = if (txn.isCredit) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurface
            )
        }
    )
}
