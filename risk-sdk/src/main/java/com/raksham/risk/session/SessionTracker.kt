package com.raksham.risk.session

import android.app.Activity
import android.app.Application
import android.os.Bundle

/**
 * Measures the payment session on the phone: typing rhythm in the amount/note fields, long
 * pauses, and how often the user left the app (e.g. to read instructions in a chat).
 * Only these numbers are sent; no keystroke content is ever recorded.
 */
object SessionTracker {
    private const val PAUSE_MS = 2_000L
    private const val MIN_INTERVAL_MS = 20L

    private var sessionActive = false
    private var lastKeyMs = 0L
    private val intervals = mutableListOf<Long>()
    private var pauses = 0
    private var appSwitches = 0
    private var startedActivities = 0

    /** Call once from Application.onCreate so app switches are counted. */
    fun install(app: Application) {
        app.registerActivityLifecycleCallbacks(object : Application.ActivityLifecycleCallbacks {
            override fun onActivityStarted(activity: Activity) {
                startedActivities++
            }

            override fun onActivityStopped(activity: Activity) {
                startedActivities = (startedActivities - 1).coerceAtLeast(0)
                if (startedActivities == 0 && sessionActive) appSwitches++
            }

            override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {}
            override fun onActivityResumed(activity: Activity) {}
            override fun onActivityPaused(activity: Activity) {}
            override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}
            override fun onActivityDestroyed(activity: Activity) {}
        })
    }

    /** Call when the payment screen opens. */
    @Synchronized
    fun startPaymentSession() {
        sessionActive = true
        lastKeyMs = 0L
        intervals.clear()
        pauses = 0
        appSwitches = 0
    }

    /** Call on every edit of the amount or note field. */
    @Synchronized
    fun onKeystroke(nowMs: Long = System.currentTimeMillis()) {
        if (lastKeyMs > 0L) {
            val gap = nowMs - lastKeyMs
            if (gap > PAUSE_MS) pauses++ else if (gap >= MIN_INTERVAL_MS) intervals.add(gap)
        }
        lastKeyMs = nowMs
    }

    /** Average ms between keystrokes, or null if nothing was typed (sent as "not measured"). */
    @Synchronized
    fun typingMs(): Double? = if (intervals.isEmpty()) null else intervals.average()

    /** Long pauses, or null if nothing was typed. */
    @Synchronized
    fun pauses(): Int? = if (lastKeyMs == 0L) null else pauses

    @Synchronized
    fun appSwitches(): Int = appSwitches
}
