package com.raksham.upi.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary = GPayBlue,
    onPrimary = Color.White,
    primaryContainer = GPayBlueLight,
    onPrimaryContainer = GPayBlue,
    secondary = GPayBlueVariant,
    onSecondary = Color.White,
    background = SurfaceBackground,
    onBackground = TextPrimary,
    surface = SurfaceCard,
    onSurface = TextPrimary,
    error = GPayRed,
    onError = Color.White
)

@Composable
fun RakshamTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content = content
    )
}

