package com.raksham.upi.ui.screens

import com.raksham.upi.ui.formatAmount
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.NorthEast
import androidx.compose.material.icons.outlined.QrCode2
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Science
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.SouthWest
import androidx.compose.material.icons.rounded.AccountBalance
import androidx.compose.material.icons.rounded.CurrencyRupee
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.RocketLaunch
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.addPathNodes
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.upi.BuildConfig
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.data.TransactionItem
import com.raksham.upi.ui.theme.HeaderBannerBlob
import com.raksham.upi.ui.theme.HeaderBannerPink
import com.raksham.upi.ui.theme.Motion
import com.raksham.upi.ui.theme.ProfileAvatarSlate
import com.raksham.upi.ui.theme.RewardsGold
import com.raksham.upi.ui.theme.UpiMarkGreen
import com.raksham.upi.ui.theme.UpiMarkOrange
import kotlinx.coroutines.launch

// The host app copies a stock UPI app's home screen; the scam check only appears when it interrupts
// a payment. Sizes below are measured from the reference screenshots (1 iOS pt mapped to 1 dp).

private enum class HomeTab(val label: String) { Home("Home"), Money("Money"), You("You") }

private val NavBarHeight = 62.dp
private val UserInitial = MockData.currentUserName.take(1)

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
    val navInset = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()

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

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surface)) {
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
            val bottom = NavBarHeight + navInset
            when (current) {
                HomeTab.Home -> HomeTabContent(
                    bottomPadding = bottom + 88.dp,
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
                HomeTab.Money -> MoneyTabContent(bottom)
                HomeTab.You -> YouTabContent(bottom, onCopyUpiId = copyUpiId, onOpenLabClick = onOpenLabClick)
            }
        }

        if (tab == HomeTab.Home) {
            ExtendedFloatingActionButton(
                text = { Text("Scan QR") },
                icon = { Icon(Icons.Outlined.QrCodeScanner, contentDescription = null) },
                onClick = onScanQrClick,
                shape = RoundedCornerShape(16.dp),
                containerColor = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = NavBarHeight + navInset + 16.dp)
            )
        }

        SnackbarHost(
            snackbar,
            Modifier.align(Alignment.BottomCenter).padding(bottom = NavBarHeight + navInset + 72.dp)
        )

        HomeNavigationBar(
            selected = tab,
            onSelect = { tab = it },
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}

@Composable
private fun HomeNavigationBar(selected: HomeTab, onSelect: (HomeTab) -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceContainer)
            .navigationBarsPadding()
            .height(NavBarHeight)
    ) {
        HomeTab.entries.forEach { item ->
            val isSelected = item == selected
            // The pill grows out from the icon's centre, as on the reference.
            val indicator by animateFloatAsState(if (isSelected) 1f else 0f, tween(Motion.MEDIUM, easing = Motion.Emphasized), label = "indicator")
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null,
                        role = Role.Tab,
                        onClick = { onSelect(item) }
                    )
            ) {
                Spacer(Modifier.height(4.dp))
                Box(contentAlignment = Alignment.Center, modifier = Modifier.size(64.dp, 32.dp)) {
                    Box(
                        Modifier
                            .matchParentSize()
                            .scale(scaleX = indicator, scaleY = 1f)
                            .background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = indicator), CircleShape)
                    )
                    val tint = if (isSelected) MaterialTheme.colorScheme.onSecondaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                    when (item) {
                        HomeTab.Home -> Icon(Icons.Rounded.Home, contentDescription = null, tint = tint)
                        HomeTab.Money -> Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier.size(20.dp).border(1.6.dp, tint, CircleShape)
                        ) { Icon(Icons.Rounded.CurrencyRupee, contentDescription = null, tint = tint, modifier = Modifier.size(13.dp)) }
                        HomeTab.You -> Avatar(UserInitial, ProfileAvatarSlate, size = 23.dp, letterSize = 12)
                    }
                }
                Spacer(Modifier.height(5.dp))
                Text(
                    item.label,
                    style = MaterialTheme.typography.labelMedium.copy(
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                        lineHeight = 16.sp
                    ),
                    color = if (isSelected) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun HomeTabContent(
    bottomPadding: Dp,
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
        contentPadding = PaddingValues(bottom = bottomPadding),
        modifier = Modifier.fillMaxSize()
    ) {
        item { HomeHeader(onSearchClick, onAvatarClick, onScanQrClick) }

        item {
            FourColumns(Modifier.padding(top = 16.dp)) { column ->
                when (column) {
                    0 -> ActionTile(Icons.Outlined.QrCodeScanner, "Scan any\nQR code", onScanQrClick)
                    1 -> ActionTile(PayAnyoneIcon, "Pay\nanyone", onPayPhoneClick)
                    2 -> ActionTile(Icons.Rounded.AccountBalance, "Bank\ntransfer", onPayUpiClick)
                    else -> ActionTile(MobileRechargeIcon, "Mobile\nrecharge", onNotInDemo)
                }
            }
        }

        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(top = 19.dp).horizontalScroll(rememberScrollState()).padding(horizontal = 24.dp)
            ) {
                ShortcutPill("UPI Lite", "Activate", accent = true, onClick = onNotInDemo) {
                    Icon(Icons.Rounded.RocketLaunch, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                }
                ShortcutPill("Rewards", "New", onClick = onNotInDemo) {
                    Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = RewardsGold, modifier = Modifier.size(26.dp))
                }
                ShortcutPill("UPI ID", MockData.currentUserUpiId, onClick = onCopyUpiId) { UpiMark(Modifier.size(22.dp)) }
            }
        }

        item {
            Text(
                "Send money",
                style = SectionTitleStyle(),
                modifier = Modifier.padding(start = 24.dp, top = 30.dp)
            )
        }

        item {
            // Seven people and a "More" cell, four per row, on the same column grid as the tiles.
            val cells: List<Contact?> = MockData.contacts.take(7) + null
            Column(Modifier.padding(top = 25.dp)) {
                cells.chunked(4).forEach { row ->
                    FourColumns(Modifier.padding(bottom = 16.dp)) { column ->
                        if (column >= row.size) return@FourColumns
                        val contact = row[column]
                        if (contact != null) {
                            PersonCell(contact.name, onClick = { onSelectContact(contact) }) {
                                Avatar(contact.name.take(1), Color(contact.colorHex), size = 54.dp, letterSize = 28)
                            }
                        } else {
                            PersonCell("More", onClick = onPayPhoneClick) {
                                Box(
                                    contentAlignment = Alignment.Center,
                                    modifier = Modifier.size(54.dp).border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape)
                                ) {
                                    Icon(Icons.Rounded.KeyboardArrowDown, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(30.dp))
                                }
                            }
                        }
                    }
                }
            }
        }

        item {
            Text(
                "Manage your money",
                style = SectionTitleStyle(),
                modifier = Modifier.padding(start = 24.dp, top = 18.dp, bottom = 8.dp)
            )
        }
        item { LinkRow(Icons.AutoMirrored.Outlined.ReceiptLong, "See transaction history", onHistoryClick) }
        item { LinkRow(Icons.Outlined.AccountBalance, "Your bank accounts", onBankAccountsClick) }
    }
}

@Composable
private fun SectionTitleStyle() = MaterialTheme.typography.titleLarge.copy(fontSize = 21.sp, lineHeight = 28.sp, fontWeight = FontWeight.Normal)

@Composable
private fun HomeHeader(onSearchClick: () -> Unit, onAvatarClick: () -> Unit, onScanQrClick: () -> Unit) {
    Box(Modifier.fillMaxWidth().background(HeaderBannerPink).clipToBounds()) {
        BannerArt(Modifier.align(Alignment.BottomEnd))
        Column(Modifier.statusBarsPadding()) {
            Spacer(Modifier.height(11.dp))
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 24.dp, end = 24.dp)) {
                Surface(
                    onClick = onSearchClick,
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surfaceContainer,
                    shadowElevation = 3.dp,
                    modifier = Modifier.weight(1f).height(48.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 12.dp)) {
                        Icon(Icons.Outlined.Search, contentDescription = null, tint = MaterialTheme.colorScheme.onSurface)
                        Spacer(Modifier.width(16.dp))
                        Text(
                            "Pay anyone on UPI",
                            style = MaterialTheme.typography.bodyLarge.copy(fontSize = 15.sp, letterSpacing = 0.25.sp),
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Spacer(Modifier.width(14.dp))
                Avatar(
                    UserInitial,
                    ProfileAvatarSlate,
                    size = 30.dp,
                    letterSize = 16,
                    modifier = Modifier.clip(CircleShape).clickable(role = Role.Button, onClickLabel = "Open your profile", onClick = onAvatarClick)
                )
            }
            Column(Modifier.padding(start = 26.dp, top = 23.dp, bottom = 13.dp).fillMaxWidth(0.62f)) {
                Text(
                    "Tip · Raksham UPI",
                    style = MaterialTheme.typography.bodySmall.copy(lineHeight = 16.sp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(11.dp))
                Text(
                    "Pay at any shop with one quick scan",
                    style = MaterialTheme.typography.titleLarge.copy(fontSize = 21.sp, lineHeight = 27.sp, fontWeight = FontWeight.Normal),
                    minLines = 2,
                    maxLines = 2
                )
                Spacer(Modifier.height(5.dp))
                Text(
                    "Scan a QR code",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Medium, lineHeight = 20.sp),
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable(role = Role.Button, onClick = onScanQrClick)
                )
            }
        }
    }
}

/** Soft blobs and a tilted phone showing a QR code, drawn in place of a photo banner. */
@Composable
private fun BannerArt(modifier: Modifier = Modifier) {
    Box(modifier.size(width = 160.dp, height = 172.dp)) {
        Canvas(Modifier.matchParentSize()) {
            drawCircle(HeaderBannerBlob, radius = size.width * 0.4f, center = Offset(size.width * 0.6f, size.height * 0.58f))
            drawCircle(HeaderBannerBlob, radius = size.width * 0.22f, center = Offset(size.width * 0.86f, size.height * 0.3f))
            drawCircle(HeaderBannerBlob, radius = size.width * 0.07f, center = Offset(size.width * 0.06f, size.height * 0.42f))
            drawCircle(HeaderBannerBlob, radius = size.width * 0.05f, center = Offset(size.width * 0.14f, size.height * 0.86f))
        }
        Surface(
            shape = RoundedCornerShape(12.dp),
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(3.dp, MaterialTheme.colorScheme.onSurface),
            shadowElevation = 4.dp,
            modifier = Modifier.align(Alignment.BottomCenter).offset(x = 10.dp, y = 26.dp).size(width = 64.dp, height = 116.dp).rotate(-10f)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Outlined.QrCode2, contentDescription = null, tint = MaterialTheme.colorScheme.onSurface, modifier = Modifier.size(40.dp))
            }
        }
    }
}

/** Four equal columns with 5 dp side margins: the column grid shared by the tiles and people. */
@Composable
private fun FourColumns(modifier: Modifier = Modifier, cell: @Composable (Int) -> Unit) {
    Row(modifier.fillMaxWidth().padding(horizontal = 5.dp)) {
        repeat(4) { column ->
            Box(contentAlignment = Alignment.TopCenter, modifier = Modifier.weight(1f)) { cell(column) }
        }
    }
}

@Composable
private fun ActionTile(icon: ImageVector, label: String, onClick: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.clip(MaterialTheme.shapes.medium).clickable(role = Role.Button, onClick = onClick)
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(62.dp).background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(16.dp))
        ) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer, modifier = Modifier.size(27.dp))
        }
        Spacer(Modifier.height(8.dp))
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 20.sp),
            textAlign = TextAlign.Center,
            minLines = 2,
            maxLines = 2,
            modifier = Modifier.widthIn(min = 80.dp)
        )
    }
}

@Composable
private fun ShortcutPill(title: String, value: String, onClick: () -> Unit, accent: Boolean = false, icon: @Composable () -> Unit) {
    Surface(
        onClick = onClick,
        shape = CircleShape,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.height(58.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 9.dp, end = 19.dp)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f), CircleShape)
            ) { icon() }
            Spacer(Modifier.width(9.dp))
            Column {
                val style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.5.sp, lineHeight = 17.sp)
                Text(title, style = style, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                Text(
                    value,
                    style = style,
                    color = if (accent) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

/** The UPI mark: an orange and a green chevron. */
@Composable
private fun UpiMark(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        fun chevron(x0: Float) = Path().apply {
            moveTo(x0, 0f); lineTo(x0 + w * 0.42f, h * 0.5f); lineTo(x0, h); close()
        }
        drawPath(chevron(w * 0.12f), UpiMarkOrange)
        drawPath(chevron(w * 0.42f), UpiMarkGreen)
    }
}

@Composable
private fun PersonCell(label: String, onClick: () -> Unit, avatar: @Composable () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(MaterialTheme.shapes.medium)
            .clickable(role = Role.Button, onClick = onClick)
            .padding(horizontal = 4.dp)
    ) {
        avatar()
        Spacer(Modifier.height(9.dp))
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium.copy(letterSpacing = 0.5.sp, lineHeight = 20.sp),
            textAlign = TextAlign.Center,
            minLines = 2,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun LinkRow(icon: ImageVector, label: String, onClick: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).heightIn(min = 56.dp).padding(horizontal = 24.dp)
    ) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.width(20.dp))
        Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Avatar(initial: String, color: Color, size: Dp, letterSize: Int, modifier: Modifier = Modifier) {
    Box(contentAlignment = Alignment.Center, modifier = modifier.size(size).background(color, CircleShape)) {
        Text(initial, color = Color.White, style = MaterialTheme.typography.bodyLarge.copy(fontSize = letterSize.sp, lineHeight = letterSize.sp, letterSpacing = 0.sp))
    }
}

@Composable
private fun TabTitle(text: String) {
    Text(text, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.statusBarsPadding().padding(start = 24.dp, end = 24.dp, top = 24.dp, bottom = 12.dp))
}

@Composable
private fun MoneyTabContent(bottomPadding: Dp) {
    LazyColumn(contentPadding = PaddingValues(bottom = bottomPadding), modifier = Modifier.fillMaxSize()) {
        item { TabTitle("Transaction history") }
        items(MockData.recentTransactions, key = { it.id }) { TransactionRow(it) }
    }
}

@Composable
private fun YouTabContent(bottomPadding: Dp, onCopyUpiId: () -> Unit, onOpenLabClick: () -> Unit) {
    LazyColumn(contentPadding = PaddingValues(bottom = bottomPadding), modifier = Modifier.fillMaxSize()) {
        item {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth().statusBarsPadding().padding(top = 32.dp, bottom = 16.dp)
            ) {
                Avatar(UserInitial, ProfileAvatarSlate, size = 88.dp, letterSize = 40)
                Spacer(Modifier.height(16.dp))
                Text(MockData.currentUserName.removeSuffix(" (You)"), style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(12.dp))
                ShortcutPill("UPI ID", MockData.currentUserUpiId, onClick = onCopyUpiId) { UpiMark(Modifier.size(22.dp)) }
            }
        }
        item { Text("Bank accounts", style = SectionTitleStyle(), modifier = Modifier.padding(start = 24.dp, top = 16.dp, bottom = 4.dp)) }
        items(MockData.linkedBankAccounts, key = { it.id }) { account ->
            ListItem(
                leadingContent = { Icon(Icons.Outlined.AccountBalance, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
                headlineContent = { Text(account.bankName) },
                supportingContent = { Text("${account.accountType} ${account.accountNumberMasked}") },
                trailingContent = if (account.isPrimary) {
                    { Text("Primary", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary) }
                } else null,
                modifier = Modifier.padding(horizontal = 8.dp)
            )
        }
        if (BuildConfig.DEBUG) {
            item { Text("Demo tools", style = SectionTitleStyle(), modifier = Modifier.padding(start = 24.dp, top = 16.dp, bottom = 4.dp)) }
            item {
                ListItem(
                    leadingContent = { Icon(Icons.Outlined.Science, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
                    headlineContent = { Text("Simulation Lab") },
                    supportingContent = { Text("Scripted scam scenarios and the Risk API address") },
                    modifier = Modifier.clickable(onClick = onOpenLabClick).padding(horizontal = 8.dp)
                )
            }
        }
    }
}

/** Outline icon drawn from SVG path data; Icon tints the whole vector. */
private fun strokeIcon(name: String, vararg paths: String): ImageVector =
    ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f).apply {
        paths.forEach {
            addPath(
                pathData = addPathNodes(it),
                stroke = SolidColor(Color.Black),
                strokeLineWidth = 1.8f,
                strokeLineCap = StrokeCap.Round,
                strokeLineJoin = StrokeJoin.Round
            )
        }
    }.build()

// A rupee note leaving its frame (send money) and a phone with a charge bolt (recharge).
private val PayAnyoneIcon = strokeIcon(
    "pay_anyone",
    "M14 4H6.5A2.5 2.5 0 0 0 4 6.5v11A2.5 2.5 0 0 0 6.5 20h11a2.5 2.5 0 0 0 2.5-2.5V11",
    "M19.5 9V2.5M16.8 5.2l2.7-2.7 2.7 2.7",
    "M8.5 8.5h6M8.5 11.2h6M10.5 8.5c2.2 0 3.1 1.1 3.1 2.7s-1.1 2.7-3.1 2.7H9.3l4.4 3.3"
)
private val MobileRechargeIcon = strokeIcon(
    "mobile_recharge",
    "M8 2.5h8A2 2 0 0 1 18 4.5v15a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-15a2 2 0 0 1 2-2z",
    "M6 5.5h12M6 18.5h12",
    "M12.8 8.2l-2.6 4h3.6l-2.6 4"
)

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
                (if (txn.isCredit) "+₹" else "₹") + formatAmount(txn.amount),
                style = MaterialTheme.typography.titleMedium,
                color = if (txn.isCredit) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurface
            )
        },
        modifier = Modifier.padding(horizontal = 8.dp)
    )
}
