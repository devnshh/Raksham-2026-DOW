package com.raksham.upi.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import com.raksham.upi.R

// Google Sans (SIL OFL 1.1, licence in licenses/google_sans_OFL.txt). One variable file covers
// Latin, Devanagari and the rupee sign, so Hindi and English render in the same family.
@OptIn(ExperimentalTextApi::class)
private fun googleSans(weight: Int) = Font(
    R.font.google_sans,
    weight = FontWeight(weight),
    variationSettings = FontVariation.Settings(FontVariation.weight(weight))
)

val GoogleSans = FontFamily(googleSans(400), googleSans(500), googleSans(600), googleSans(700))

private val Base = Typography()

private fun TextStyle.sans() = copy(fontFamily = GoogleSans)

// Material 3 type scale in Google Sans. Sizes stay in sp so text follows the system font size.
val AppTypography = Typography(
    displayLarge = Base.displayLarge.sans(),
    displayMedium = Base.displayMedium.sans(),
    displaySmall = Base.displaySmall.sans(),
    headlineLarge = Base.headlineLarge.sans(),
    headlineMedium = Base.headlineMedium.sans(),
    headlineSmall = Base.headlineSmall.sans(),
    titleLarge = Base.titleLarge.sans(),
    titleMedium = Base.titleMedium.sans().copy(fontWeight = FontWeight.SemiBold),
    titleSmall = Base.titleSmall.sans().copy(fontWeight = FontWeight.SemiBold),
    bodyLarge = Base.bodyLarge.sans(),
    bodyMedium = Base.bodyMedium.sans(),
    bodySmall = Base.bodySmall.sans(),
    labelLarge = Base.labelLarge.sans().copy(fontWeight = FontWeight.SemiBold),
    labelMedium = Base.labelMedium.sans(),
    labelSmall = Base.labelSmall.sans()
)
