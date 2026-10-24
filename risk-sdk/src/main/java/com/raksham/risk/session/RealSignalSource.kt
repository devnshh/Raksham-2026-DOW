package com.raksham.risk.session

import android.content.Context
import android.hardware.display.DisplayManager
import android.media.AudioManager
import android.view.Display

/**
 * Reads real session signals on the phone. Only derived values leave the device.
 *  - on_call: AudioManager mode (covers phone and VoIP calls, no call-log permission).
 *  - screen_shared: an extra display is attached (casting / mirroring). This is a proxy: a
 *    screen-share app that records without a second display is not visible here before Android 15.
 *  - remote_app_present / remote_app_new: known remote-access apps (needs <queries> in the manifest);
 *    "new" means installed in the last 24 hours.
 *  - typing_ms / pauses / app_switches: from SessionTracker.
 *  - device_new / failed_auth are not measured in this demo and stay false / 0.
 */
class RealSignalSource(private val context: Context? = null) : SessionSignalSource {

    companion object {
        /** Keep in sync with <queries> in risk-sdk/src/main/AndroidManifest.xml. */
        val REMOTE_APPS = listOf(
            "com.anydesk.anydeskandroid",
            "com.teamviewer.quicksupport.market",
            "com.teamviewer.host.market",
            "com.carriez.flutter_hbb",
            "com.rustdesk.rustdesk",
            "com.sand.airdroid",
            "com.sand.airdroidbiz"
        )
        private const val DAY_MS = 24L * 60 * 60 * 1000
    }

    override fun collectSignals(): SessionSignals {
        val ctx = context
        val audioManager = ctx?.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
        val onCall = audioManager?.mode == AudioManager.MODE_IN_CALL ||
            audioManager?.mode == AudioManager.MODE_IN_COMMUNICATION

        val displayManager = ctx?.getSystemService(Context.DISPLAY_SERVICE) as? DisplayManager
        val extraDisplay = (displayManager?.displays?.count { it.displayId != Display.DEFAULT_DISPLAY } ?: 0) > 0

        val now = System.currentTimeMillis()
        val installTimes = REMOTE_APPS.mapNotNull { pkg ->
            try {
                ctx?.packageManager?.getPackageInfo(pkg, 0)?.firstInstallTime
            } catch (e: Exception) {
                null
            }
        }

        return SessionSignals(
            on_call = onCall,
            screen_shared = extraDisplay,
            remote_app_present = installTimes.isNotEmpty(),
            remote_app_new = installTimes.any { now - it < DAY_MS },
            app_switches = SessionTracker.appSwitches(),
            typing_ms = SessionTracker.typingMs(),
            pauses = SessionTracker.pauses(),
            pin_secs = null,
            device_new = false,
            failed_auth = 0
        )
    }
}
