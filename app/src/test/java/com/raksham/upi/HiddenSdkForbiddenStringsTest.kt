package com.raksham.upi

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class HiddenSdkForbiddenStringsTest {

    private val paymentScreenFiles = listOf(
        "src/main/java/com/raksham/upi/ui/screens/PaymentAmountScreen.kt",
        "src/main/java/com/raksham/upi/ui/screens/PayPhoneScreen.kt",
        "src/main/java/com/raksham/upi/ui/screens/PayUpiScreen.kt",
        "src/main/java/com/raksham/upi/ui/screens/ScanQrScreen.kt",
        "src/main/java/com/raksham/upi/ui/screens/TransactionSuccessScreen.kt",
        "src/main/java/com/raksham/upi/ui/screens/HomeScreen.kt",
        "src/main/java/com/raksham/upi/ui/components/AmberWarningDialog.kt",
        "src/main/java/com/raksham/upi/ui/components/RedSmartPauseDialog.kt",
        "src/main/java/com/raksham/upi/ui/components/NpciPinKeypad.kt",
        "src/main/java/com/raksham/upi/ui/components/TrustedContactSheet.kt",
        "src/main/java/com/raksham/upi/ui/components/ReportScamSheet.kt",
        "src/main/java/com/raksham/upi/ui/templates/TemplateRegistry.kt"
    )

    private val rawReasonCodes = listOf(
        "ON_CALL",
        "SCREEN_SHARED",
        "REMOTE_APP_PRESENT",
        "REMOTE_APP_NEW",
        "LOOKALIKE_HANDLE",
        "NEW_PAYEE_YOUNG_ACCOUNT",
        "ANALYST_CONFIRMED_SCAM",
        "MANY_NEW_PAYERS"
    )

    @Test
    fun testNoForbiddenStringsInPaymentFlowScreens() {
        val projectAppDir = File("app")
        val baseDir = if (projectAppDir.exists()) projectAppDir else File(".")

        paymentScreenFiles.forEach { relativePath ->
            val file = File(baseDir, relativePath)
            if (file.exists()) {
                val lines = file.readLines()
                lines.forEachIndexed { index, line ->
                    val lineNum = index + 1
                    val trimmed = line.trim()
                    // Ignore comments or imports if any
                    if (!trimmed.startsWith("//") && !trimmed.startsWith("/*") && !trimmed.startsWith("*")) {
                        // Check for forbidden word "Satark"
                        val containsSatark = line.contains("Satark", ignoreCase = false)
                        assertTrue(
                            "File $relativePath:$lineNum must not contain 'Satark': $line",
                            !containsSatark
                        )

                        // Check for forbidden words "fusion"
                        val containsFusion = line.contains("fusion", ignoreCase = true)
                        assertTrue(
                            "File $relativePath:$lineNum must not contain 'fusion': $line",
                            !containsFusion
                        )

                        // Check that raw reason codes are never directly rendered in UI text
                        rawReasonCodes.forEach { code ->
                            val containsRawCode = line.contains("\"$code\"")
                            assertTrue(
                                "File $relativePath:$lineNum must not contain raw reason code '$code': $line",
                                !containsRawCode
                            )
                        }
                    }
                }
            }
        }
    }
}
