package com.raksham.upi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.raksham.risk.session.ScriptedSignalSource
import com.raksham.risk.session.SessionSignalSourceProvider
import com.raksham.upi.data.Contact
import com.raksham.upi.data.MockData
import com.raksham.upi.ui.screens.*
import com.raksham.upi.ui.theme.Motion
import com.raksham.upi.ui.theme.RakshamTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Light theme only, so system bar icons stay dark even when the phone is in dark mode.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT)
        )

        setContent {
            RakshamTheme {
                val navController = rememberNavController()

                // State to pass selected contact and amount to payment amount screen
                var activeContact by remember { mutableStateOf<Contact?>(null) }
                var activeAmount by remember { mutableStateOf<Double?>(null) }
                var activeEntryChannel by remember { mutableStateOf("typed_vpa") }
                var activeNote by remember { mutableStateOf("") }
                var customScenarioActive by remember { mutableStateOf(false) }

                // Success receipt state
                var successAmount by remember { mutableDoubleStateOf(0.0) }
                var successContact by remember { mutableStateOf<Contact?>(null) }
                var successRefId by remember { mutableStateOf("") }

                // Shared-axis X: the new screen slides in a short distance and fades up; Back reverses it.
                NavHost(
                    navController = navController,
                    startDestination = "home",
                    modifier = Modifier.background(MaterialTheme.colorScheme.surface),
                    enterTransition = {
                        slideInHorizontally(tween(Motion.LONG, easing = Motion.Emphasized)) { it / 8 } +
                            fadeIn(tween(Motion.MEDIUM, delayMillis = 60, easing = Motion.EmphasizedDecelerate))
                    },
                    exitTransition = {
                        slideOutHorizontally(tween(Motion.LONG, easing = Motion.Emphasized)) { -it / 8 } +
                            fadeOut(tween(Motion.SHORT, easing = Motion.EmphasizedAccelerate))
                    },
                    popEnterTransition = {
                        slideInHorizontally(tween(Motion.LONG, easing = Motion.Emphasized)) { -it / 8 } +
                            fadeIn(tween(Motion.MEDIUM, delayMillis = 60, easing = Motion.EmphasizedDecelerate))
                    },
                    popExitTransition = {
                        slideOutHorizontally(tween(Motion.LONG, easing = Motion.Emphasized)) { it / 8 } +
                            fadeOut(tween(Motion.SHORT, easing = Motion.EmphasizedAccelerate))
                    }
                ) {
                    // Home: payments, history and profile tabs
                    composable("home") {
                        HomeScreen(
                            onPayPhoneClick = {
                                navController.navigate("pay_phone")
                            },
                            onPayUpiClick = {
                                navController.navigate("pay_upi")
                            },
                            onScanQrClick = {
                                navController.navigate("scan_qr")
                            },
                            onSelectContact = { contact ->
                                activeContact = contact
                                activeAmount = null
                                activeEntryChannel = "contact"
                                navController.navigate("payment_amount")
                            },
                            onOpenLabClick = {
                                navController.navigate("satark_lab")
                            }
                        )
                    }

                    // 1. Pay Phone Number Flow
                    composable("pay_phone") {
                        PayPhoneScreen(
                            onBackClick = { navController.popBackStack() },
                            onContactSelected = { contact ->
                                activeContact = contact
                                activeAmount = null
                                activeEntryChannel = "phone_number"
                                navController.navigate("payment_amount")
                            }
                        )
                    }

                    // 2. Pay UPI ID / VPA Flow
                    composable("pay_upi") {
                        PayUpiScreen(
                            onBackClick = { navController.popBackStack() },
                            onProceedToAmount = { contact ->
                                activeContact = contact
                                activeAmount = null
                                activeEntryChannel = "typed_vpa"
                                navController.navigate("payment_amount")
                            }
                        )
                    }

                    // 3. Scan QR Flow
                    composable("scan_qr") {
                        ScanQrScreen(
                            onBackClick = { navController.popBackStack() },
                            onQrResolved = { contact, defaultAmt, channel ->
                                activeContact = contact
                                activeAmount = defaultAmt
                                activeEntryChannel = channel
                                navController.navigate("payment_amount")
                            }
                        )
                    }

                    // Payment Amount & Satark Risk Interception Screen
                    composable("payment_amount") {
                        val contact = activeContact ?: MockData.contacts.first()
                        DisposableEffect(Unit) {
                            onDispose {
                                if (customScenarioActive) {
                                    SessionSignalSourceProvider.restoreRealSource()
                                    customScenarioActive = false
                                    activeNote = ""
                                }
                            }
                        }
                        PaymentAmountScreen(
                            contact = contact,
                            initialAmount = activeAmount,
                            initialNote = activeNote,
                            entryChannel = activeEntryChannel,
                            onBackClick = { navController.popBackStack() },
                            onPaymentSuccess = { amount, paidContact, refId ->
                                successAmount = amount
                                successContact = paidContact
                                successRefId = refId
                                navController.navigate("success") {
                                    popUpTo("home")
                                }
                            }
                        )
                    }

                    // Transaction Success & Digital Receipt Screen
                    composable("success") {
                        val contact = successContact ?: MockData.contacts.first()
                        TransactionSuccessScreen(
                            amount = successAmount,
                            contact = contact,
                            upiRefId = successRefId,
                            onDoneClick = {
                                navController.navigate("home") {
                                    popUpTo("home") { inclusive = true }
                                }
                            }
                        )
                    }

                    // Satark Simulation Lab Screen (Only reachable in DEBUG mode)
                    composable("satark_lab") {
                        if (BuildConfig.DEBUG) {
                            SimulationLabScreen(
                                onBackClick = { navController.popBackStack() },
                                onOpenCustom = { contact, amount, channel, note, signals ->
                                    // Scripted signals for this one payment; restored when the payment screen closes.
                                    SessionSignalSourceProvider.setScriptedSource(ScriptedSignalSource(signals))
                                    customScenarioActive = true
                                    activeContact = contact
                                    activeAmount = amount
                                    activeEntryChannel = channel
                                    activeNote = note
                                    navController.navigate("payment_amount")
                                }
                            )
                        } else {
                            LaunchedEffect(Unit) {
                                navController.popBackStack()
                            }
                        }
                    }
                }
            }
        }
    }
}

