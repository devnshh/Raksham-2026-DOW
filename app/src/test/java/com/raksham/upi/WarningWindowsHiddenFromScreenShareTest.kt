package com.raksham.upi

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Every warning window (and the PIN pad) must be a secure window, so screen sharing, casting and
 * recording show it blank and a scammer watching the screen cannot read it.
 */
class WarningWindowsHiddenFromScreenShareTest {

    private val base = File(if (File("app").exists()) "app" else ".", "src/main/java/com/raksham/upi/ui/components")

    /** File -> number of windows it opens (each needs its own secure policy). */
    private val windows = mapOf(
        "AmberWarningDialog.kt" to 1,
        "RedSmartPauseDialog.kt" to 2,   // the pause itself and the final-release notice
        "DeclinedPaymentDialog.kt" to 1,
        "NpciPinKeypad.kt" to 1
    )

    @Test
    fun everyWarningWindowIsSecure() {
        windows.forEach { (file, count) ->
            val text = File(base, file).readText()
            val secure = Regex("securePolicy = SecureFlagPolicy.SecureOn").findAll(text).count()
            assertTrue("$file opens $count window(s) but only $secure are secure", secure >= count)
        }
    }
}
