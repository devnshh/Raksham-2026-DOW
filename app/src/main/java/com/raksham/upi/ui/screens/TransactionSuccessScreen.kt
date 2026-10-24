package com.raksham.upi.ui.screens

import android.content.Intent
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathMeasure
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.raksham.upi.data.Contact
import com.raksham.upi.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun TransactionSuccessScreen(
    amount: Double,
    contact: Contact,
    upiRefId: String,
    onDoneClick: () -> Unit
) {
    val context = LocalContext.current

    // One staggered sequence, about 1 s end to end. Delays live in the specs so the system
    // animator scale stretches or skips them along with the motion.
    val circle = remember { Animatable(0f) }
    val check = remember { Animatable(0f) }
    val amountIn = remember { Animatable(0f) }
    val paidIn = remember { Animatable(0f) }
    val cardIn = remember { Animatable(0f) }

    LaunchedEffect(Unit) {
        val rise = { delay: Int -> tween<Float>(Motion.MEDIUM, delay, Motion.EmphasizedDecelerate) }
        launch {
            circle.animateTo(1f, spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessMedium))
        }
        launch { check.animateTo(1f, tween(500, delayMillis = 120, easing = Motion.EmphasizedDecelerate)) }
        launch { amountIn.animateTo(1f, rise(420)) }
        launch { paidIn.animateTo(1f, rise(500)) }
        launch { cardIn.animateTo(1f, rise(600)) }
    }

    val timestamp = remember {
        val sdf = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault())
        sdf.format(Date())
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.tertiaryContainer,
        contentColor = MaterialTheme.colorScheme.onTertiaryContainer
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Spacer(modifier = Modifier.height(32.dp))

                SuccessMark(circleScale = { circle.value }, checkProgress = { check.value })

                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "₹${String.format("%.2f", amount)}",
                    style = MaterialTheme.typography.displayMedium,
                    modifier = Modifier.fadeUp { amountIn.value }
                )

                Text(
                    text = "Paid to ${contact.name}",
                    style = MaterialTheme.typography.titleLarge,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .padding(top = 4.dp)
                        .fadeUp { paidIn.value }
                )

                Spacer(modifier = Modifier.height(32.dp))

                Surface(
                    shape = MaterialTheme.shapes.extraLarge,
                    color = MaterialTheme.colorScheme.surface,
                    contentColor = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier
                        .fillMaxWidth()
                        .fadeUp { cardIn.value }
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        ReceiptDetailRow("UPI transaction ID", upiRefId)
                        HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp), color = MaterialTheme.colorScheme.outlineVariant)
                        ReceiptDetailRow("To", "${contact.name}\n${contact.upiId}")
                        HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp), color = MaterialTheme.colorScheme.outlineVariant)
                        ReceiptDetailRow("From", "State Bank of India •••• 4291")
                        HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp), color = MaterialTheme.colorScheme.outlineVariant)
                        ReceiptDetailRow("Date", timestamp)
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
            }

            Column(modifier = Modifier
                .fillMaxWidth()
                .fadeUp { cardIn.value }) {
                TextButton(
                    onClick = {
                        val shareIntent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(
                                Intent.EXTRA_TEXT,
                                "Paid ₹$amount to ${contact.name} (${contact.upiId}) via Raksham UPI. UPI Ref: $upiRefId. Protected by Raksham security."
                            )
                        }
                        context.startActivity(Intent.createChooser(shareIntent, "Share Receipt"))
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.onTertiaryContainer),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                ) {
                    Icon(Icons.Filled.Share, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Share receipt")
                }

                Spacer(modifier = Modifier.height(8.dp))

                Button(
                    onClick = onDoneClick,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.tertiary,
                        contentColor = MaterialTheme.colorScheme.onTertiary
                    ),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                ) {
                    Text("Done", style = MaterialTheme.typography.titleMedium)
                }
            }
        }
    }
}

private fun Modifier.fadeUp(progress: () -> Float) = graphicsLayer {
    val p = progress()
    alpha = p
    translationY = (1f - p) * 24.dp.toPx()
}

/** Filled circle that springs in, with a check mark whose stroke is drawn progressively. */
@Composable
private fun SuccessMark(circleScale: () -> Float, checkProgress: () -> Float) {
    val fill = MaterialTheme.colorScheme.tertiary
    val stroke = MaterialTheme.colorScheme.onTertiary
    Canvas(
        modifier = Modifier
            .size(112.dp)
            .graphicsLayer {
                val s = circleScale()
                scaleX = s
                scaleY = s
            }
            .semantics { contentDescription = "Success" }
    ) {
        drawCircle(fill)
        val w = size.width
        val h = size.height
        val tick = Path().apply {
            moveTo(w * 0.28f, h * 0.52f)
            lineTo(w * 0.44f, h * 0.68f)
            lineTo(w * 0.73f, h * 0.35f)
        }
        val measure = PathMeasure().apply { setPath(tick, false) }
        val visible = Path()
        measure.getSegment(0f, measure.length * checkProgress(), visible, true)
        drawPath(
            visible,
            color = stroke,
            style = Stroke(width = 7.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
    }
}

@Composable
private fun ReceiptDetailRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(16.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            textAlign = TextAlign.End,
            modifier = Modifier.weight(1f)
        )
    }
}
