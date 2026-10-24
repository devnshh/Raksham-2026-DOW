package com.raksham.upi.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.raksham.risk.model.PlainReason
import com.raksham.risk.model.RiskDecision
import com.raksham.upi.ui.templates.TemplateRegistry
import com.raksham.upi.ui.theme.*

/** English line with the Hindi line directly under it, same style so neither reads as secondary. */
@Composable
internal fun BilingualText(
    en: String,
    hi: String,
    style: TextStyle,
    modifier: Modifier = Modifier,
    color: Color = Color.Unspecified,
    fontWeight: FontWeight? = null,
    textAlign: TextAlign? = null
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(text = en, style = style, color = color, fontWeight = fontWeight, textAlign = textAlign)
        Text(text = hi, style = style, color = color, fontWeight = fontWeight, textAlign = textAlign)
    }
}

/** Two-line button label (English, Hindi). Colour comes from the button's content colour. */
@Composable
internal fun BilingualLabel(en: String, hi: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = en, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
        Text(text = hi, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
    }
}

/** Reasons from the decision: icon + English + Hindi, one row each. */
@Composable
internal fun ReasonList(
    reasons: List<PlainReason>,
    iconTint: Color,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        reasons.forEach { reason ->
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.Top) {
                Icon(
                    imageVector = Icons.Default.ErrorOutline,
                    contentDescription = null,
                    tint = iconTint,
                    modifier = Modifier
                        .padding(top = 2.dp)
                        .size(24.dp)
                )
                BilingualText(
                    en = reason.en,
                    hi = reason.hi,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AmberWarningDialog(
    decision: RiskDecision,
    payeeName: String = "",
    amount: Double = 0.0,
    onContinue: () -> Unit,
    onCancel: () -> Unit,
    onThisWasMe: () -> Unit = onContinue
) {
    val template = TemplateRegistry.resolve(decision.templateId)
    val reasonsToShow = decision.reasons.take(3)
    val cautionColors = LocalCautionColors.current

    // Swipe-down or tapping outside is the safe choice: it cancels the payment.
    ModalBottomSheet(
        onDismissRequest = onCancel,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
                .padding(top = 8.dp, bottom = 24.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .background(cautionColors.cautionContainer, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = "Caution Notice",
                    tint = cautionColors.onCautionContainer,
                    modifier = Modifier.size(32.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            BilingualText(
                en = template.titleEn,
                hi = template.titleHi,
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.semantics { heading() }
            )

            Spacer(modifier = Modifier.height(12.dp))

            BilingualText(
                en = template.bodyEn,
                hi = template.bodyHi,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            if (reasonsToShow.isNotEmpty() && !decision.isCheckUnavailable) {
                Spacer(modifier = Modifier.height(20.dp))
                ReasonList(reasons = reasonsToShow, iconTint = cautionColors.caution)
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Safe action first and filled; continuing is a quiet text button, single tap.
            Button(
                onClick = onCancel,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp)
                    .semantics { contentDescription = "Cancel payment" }
            ) {
                BilingualLabel(en = "Cancel Payment", hi = "भुगतान रद्द करें")
            }

            Spacer(modifier = Modifier.height(8.dp))

            TextButton(
                onClick = onContinue,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp)
                    .semantics { contentDescription = "Continue anyway" }
            ) {
                BilingualLabel(en = "Continue anyway", hi = "फिर भी जारी रखें")
            }

            // "This was me": continues and stops later ambers for this payee. Not offered when the
            // check could not run, or during a call or remote session (a scammer could coach the tap).
            if (!decision.isCheckUnavailable && !decision.sessionUnderPressure) {
                TextButton(
                    onClick = onThisWasMe,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 48.dp)
                        .semantics { contentDescription = "This was me, I know this payee. Continue" }
                ) {
                    BilingualLabel(en = "This was me, I know this payee", hi = "यह मैं हूँ, मैं इन्हें जानता हूँ")
                }
            }
        }
    }
}
