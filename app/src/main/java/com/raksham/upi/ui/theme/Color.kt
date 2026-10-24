package com.raksham.upi.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

// Material 3 colour roles for a blue-seeded scheme (Google Pay-like look, no Google branding).
// Screens read colours from MaterialTheme.colorScheme or LocalCautionColors, never raw hex.

internal val LightColors = lightColorScheme(
    primary = Color(0xFF0B57D0),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFD3E3FD),
    onPrimaryContainer = Color(0xFF0842A0),
    secondary = Color(0xFF00639B),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFC2E7FF),
    onSecondaryContainer = Color(0xFF001D35),
    tertiary = Color(0xFF146C2E),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFC4EED0),
    onTertiaryContainer = Color(0xFF072711),
    error = Color(0xFFB3261E),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFF9DEDC),
    onErrorContainer = Color(0xFF410E0B),
    background = Color(0xFFFFFFFF),
    onBackground = Color(0xFF1F1F1F),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF1F1F1F),
    surfaceVariant = Color(0xFFE3E3E3),
    onSurfaceVariant = Color(0xFF444746),
    surfaceTint = Color(0xFF0B57D0),
    outline = Color(0xFF747775),
    outlineVariant = Color(0xFFC4C7C5),
    inverseSurface = Color(0xFF303030),
    inverseOnSurface = Color(0xFFF2F2F2),
    inversePrimary = Color(0xFFA8C7FA),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFFFFFFF),
    surfaceDim = Color(0xFFD3DBE5),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFF8FAFD),
    surfaceContainer = Color(0xFFF0F4F9),
    surfaceContainerHigh = Color(0xFFE9EEF6),
    surfaceContainerHighest = Color(0xFFDDE3EA)
)

internal val DarkColors = darkColorScheme(
    primary = Color(0xFFA8C7FA),
    onPrimary = Color(0xFF062E6F),
    primaryContainer = Color(0xFF0842A0),
    onPrimaryContainer = Color(0xFFD3E3FD),
    secondary = Color(0xFF7FCFFF),
    onSecondary = Color(0xFF003355),
    secondaryContainer = Color(0xFF004A77),
    onSecondaryContainer = Color(0xFFC2E7FF),
    tertiary = Color(0xFF6DD58C),
    onTertiary = Color(0xFF0A3818),
    tertiaryContainer = Color(0xFF0F5223),
    onTertiaryContainer = Color(0xFFC4EED0),
    error = Color(0xFFF2B8B5),
    onError = Color(0xFF601410),
    errorContainer = Color(0xFF8C1D18),
    onErrorContainer = Color(0xFFF9DEDC),
    background = Color(0xFF131314),
    onBackground = Color(0xFFE3E3E3),
    surface = Color(0xFF131314),
    onSurface = Color(0xFFE3E3E3),
    surfaceVariant = Color(0xFF444746),
    onSurfaceVariant = Color(0xFFC4C7C5),
    surfaceTint = Color(0xFFA8C7FA),
    outline = Color(0xFF8E918F),
    outlineVariant = Color(0xFF444746),
    inverseSurface = Color(0xFFE3E3E3),
    inverseOnSurface = Color(0xFF303030),
    inversePrimary = Color(0xFF0B57D0),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF37393B),
    surfaceDim = Color(0xFF131314),
    surfaceContainerLowest = Color(0xFF0E0E0E),
    surfaceContainerLow = Color(0xFF1B1B1B),
    surfaceContainer = Color(0xFF1E1F20),
    surfaceContainerHigh = Color(0xFF282A2C),
    surfaceContainerHighest = Color(0xFF333537)
)

/**
 * Satark tier colours that Material has no role for. Red (danger) uses the error roles and
 * green (safe) uses the tertiary roles; amber (caution) lives here.
 */
@Immutable
data class CautionColors(
    val caution: Color,
    val onCaution: Color,
    val cautionContainer: Color,
    val onCautionContainer: Color
)

internal val LightCautionColors = CautionColors(
    caution = Color(0xFF8A5100),
    onCaution = Color(0xFFFFFFFF),
    cautionContainer = Color(0xFFFFDDB3),
    onCautionContainer = Color(0xFF2B1700)
)

internal val DarkCautionColors = CautionColors(
    caution = Color(0xFFFFB95C),
    onCaution = Color(0xFF482900),
    cautionContainer = Color(0xFF673D00),
    onCautionContainer = Color(0xFFFFDDB3)
)

// Fixed colours measured from the reference home screen that have no Material role.
val HeaderBannerPink = Color(0xFFFDEFEF)
val HeaderBannerBlob = Color(0xFFF9D9DE)
val ProfileAvatarSlate = Color(0xFF465C64)
val UpiMarkOrange = Color(0xFFF47A20)
val UpiMarkGreen = Color(0xFF0E9348)
val RewardsGold = Color(0xFFF9AB00)

val LocalCautionColors = staticCompositionLocalOf { LightCautionColors }
