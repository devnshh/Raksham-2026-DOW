package com.raksham.upi.ui.screens

import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.BlendMode
import kotlin.math.cos
import androidx.compose.ui.graphics.lerp
import kotlin.math.PI
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.outlined.FlashlightOff
import androidx.compose.material.icons.outlined.FlashlightOn
import androidx.compose.material.icons.outlined.Image
import androidx.compose.material.icons.outlined.QrCode2
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.raksham.upi.data.Contact
import com.raksham.upi.ui.formatAmount
import com.raksham.upi.ui.theme.Motion
import kotlinx.coroutines.delay

/** A demo QR code: what tapping it "scans". The entry channel is what the risk check is told. */
private data class SampleQr(
    val title: String,
    val source: String,
    val contact: Contact,
    val amount: Double,
    val entryChannel: String
)

private val ChaiPointQr = SampleQr(
    title = "Chai Point Counter",
    source = "Shop counter QR",
    contact = Contact("chai_qr", "Chai Point Counter", "Merchant QR", "chaipoint@icici", "CP", 0xFF5D4037, isVerified = true),
    amount = 45.0,
    entryChannel = "qr_scan"
)
private val CbiNoticeQr = SampleQr(
    title = "CBI Cyber Cell Notice",
    source = "QR shown by a caller",
    contact = Contact("police_qr", "CBI Cyber Cell Verification", "Notice QR", "cbi-verification-dept@ybl", "CB", 0xFF1565C0),
    amount = 48000.0,
    entryChannel = "qr_scan"
)
private val RebateQr = SampleQr(
    title = "Electricity Rebate",
    source = "QR image from WhatsApp",
    contact = Contact("rebate_qr", "Govt Rebate Officer", "QR from WhatsApp", "electricity-rebate@oksbi", "RE", 0xFF00897B),
    amount = 5000.0,
    entryChannel = "qr_gallery"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanQrScreen(
    onBackClick: () -> Unit,
    onQrResolved: (contact: Contact, defaultAmount: Double?, entryChannel: String) -> Unit
) {
    var torchOn by remember { mutableStateOf(false) }
    var detected by remember { mutableStateOf<SampleQr?>(null) }

    // A short "QR detected" beat before the payment opens, so a tap reads as a scan.
    LaunchedEffect(detected) {
        val qr = detected ?: return@LaunchedEffect
        delay(520)
        onQrResolved(qr.contact, qr.amount, qr.entryChannel)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan any QR code") },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { torchOn = !torchOn }) {
                        AnimatedContent(targetState = torchOn, transitionSpec = { fadeIn() togetherWith fadeOut() }, label = "torch") { on ->
                            Icon(
                                if (on) Icons.Outlined.FlashlightOn else Icons.Outlined.FlashlightOff,
                                contentDescription = if (on) "Turn off flashlight" else "Turn on flashlight",
                                tint = if (on) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            )
        }
    ) { padding ->
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
        ) {
            Spacer(Modifier.height(12.dp))
            Viewfinder(detected = detected != null)
            Spacer(Modifier.height(20.dp))
            AnimatedContent(
                targetState = detected,
                transitionSpec = { fadeIn(tween(Motion.SHORT)) togetherWith fadeOut(tween(Motion.SHORT)) },
                label = "scan status"
            ) { qr ->
                Text(
                    if (qr == null) "Point at any UPI QR code" else "QR detected: ${qr.title}",
                    style = MaterialTheme.typography.bodyLarge,
                    color = if (qr == null) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.primary,
                    textAlign = TextAlign.Center
                )
            }
            Spacer(Modifier.height(16.dp))
            OutlinedButton(
                onClick = { if (detected == null) detected = RebateQr },
                shape = CircleShape,
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 10.dp)
            ) {
                Icon(Icons.Outlined.Image, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Upload from gallery")
            }

            Spacer(Modifier.height(28.dp))
            Text(
                "Sample QR codes",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp)
            )
            Text(
                "Tap one to scan it",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, top = 2.dp, bottom = 8.dp)
            )
            listOf(ChaiPointQr, CbiNoticeQr, RebateQr).forEach { qr ->
                ListItem(
                    leadingContent = {
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier.size(44.dp).background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(12.dp))
                        ) { Icon(Icons.Outlined.QrCode2, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer) }
                    },
                    headlineContent = { Text(qr.title) },
                    supportingContent = { Text("${qr.source} · ₹${formatAmount(qr.amount)}") },
                    trailingContent = { Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null) },
                    modifier = Modifier
                        .padding(horizontal = 8.dp)
                        .clip(MaterialTheme.shapes.medium)
                        .clickable(enabled = detected == null) { detected = qr }
                )
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

/**
 * Tonal square with four rounded corner brackets around a QR code. While scanning, a soft ring of
 * light ripples out from the centre of the code, tinting it as it passes, and the brackets ease
 * in like a camera finding focus. On detection the code turns green, the brackets close in and a
 * check pops in.
 */
@Composable
private fun Viewfinder(detected: Boolean) {
    val reading = rememberInfiniteTransition(label = "reading")
    val wave by reading.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, easing = LinearEasing), RepeatMode.Restart),
        label = "wave"
    )
    val found by animateFloatAsState(if (detected) 1f else 0f, tween(Motion.MEDIUM, easing = Motion.EmphasizedDecelerate), label = "found")
    val bracketScale by animateFloatAsState(
        if (detected) 0.9f else 1f,
        spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessMediumLow),
        label = "brackets"
    )
    val bracketColor by animateColorAsState(
        if (detected) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary,
        tween(Motion.MEDIUM),
        label = "bracket colour"
    )
    val idle = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.14f)
    val lit = MaterialTheme.colorScheme.primary.copy(alpha = 0.85f)
    val done = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.5f)

    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(272.dp)
            .clip(RoundedCornerShape(32.dp))
            .background(MaterialTheme.colorScheme.surfaceContainer)
    ) {
        Icon(
            Icons.Outlined.QrCode2,
            contentDescription = null,
            tint = Color.Black,
            modifier = Modifier
                .size(170.dp)
                .graphicsLayer(compositingStrategy = CompositingStrategy.Offscreen)
                .drawWithContent {
                    drawContent()
                    // Recolour the code (SrcIn keeps its shape) with a radial ring centred on it.
                    val reach = size.minDimension * 0.75f
                    val front = (-0.15f + wave * 1.3f) / 1.3f
                    val band = 0.16f
                    val base = lerp(idle, done, found)
                    val ring = lerp(lit, done, found)
                    drawRect(
                        Brush.radialGradient(
                            0f to base,
                            (front - band).coerceIn(0f, 1f) to base,
                            front.coerceIn(0f, 1f) to ring,
                            (front + band).coerceIn(0f, 1f) to base,
                            1f to base,
                            center = center,
                            radius = reach
                        ),
                        blendMode = BlendMode.SrcIn
                    )
                }
        )

        // Focus pulse: the brackets ease in and back once per wave.
        val focus = 1f - 0.035f * (0.5f - 0.5f * cos(2 * PI.toFloat() * wave)) * (1f - found)
        Canvas(Modifier.fillMaxSize().padding(28.dp).scale(bracketScale * focus)) {
            val arm = size.minDimension * 0.2f
            val r = 18.dp.toPx()
            val stroke = Stroke(width = 4.5.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
            val w = size.width
            val h = size.height
            // One bracket path per corner: an arm, a rounded corner, the other arm.
            listOf(
                Path().apply { moveTo(0f, arm); lineTo(0f, r); quadraticBezierTo(0f, 0f, r, 0f); lineTo(arm, 0f) },
                Path().apply { moveTo(w - arm, 0f); lineTo(w - r, 0f); quadraticBezierTo(w, 0f, w, r); lineTo(w, arm) },
                Path().apply { moveTo(w, h - arm); lineTo(w, h - r); quadraticBezierTo(w, h, w - r, h); lineTo(w - arm, h) },
                Path().apply { moveTo(arm, h); lineTo(r, h); quadraticBezierTo(0f, h, 0f, h - r); lineTo(0f, h - arm) }
            ).forEach { drawPath(it, bracketColor, style = stroke) }
        }

        AnimatedVisibility(
            visible = detected,
            enter = scaleIn(spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessMedium)) + fadeIn()
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(64.dp).background(MaterialTheme.colorScheme.tertiary, CircleShape)
            ) {
                Icon(Icons.Rounded.Check, contentDescription = "QR detected", tint = MaterialTheme.colorScheme.onTertiary, modifier = Modifier.size(36.dp))
            }
        }
    }
}
