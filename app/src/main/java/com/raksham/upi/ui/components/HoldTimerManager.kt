package com.raksham.upi.ui.components

object HoldTimerManager {
    private var holdStartEpochMs: Long = 0L
    private var holdDurationSeconds: Int = 30 * 60

    fun startHold(durationMinutes: Int) {
        holdDurationSeconds = durationMinutes * 60
        holdStartEpochMs = System.currentTimeMillis()
    }

    fun getRemainingSeconds(): Int {
        if (holdStartEpochMs == 0L) return 0
        val elapsed = (System.currentTimeMillis() - holdStartEpochMs) / 1000
        val remaining = (holdDurationSeconds - elapsed).coerceAtLeast(0)
        return remaining.toInt()
    }

    fun isHoldCompleted(): Boolean {
        return getRemainingSeconds() <= 0
    }

    fun formatRemainingTime(): String {
        val totalSecs = getRemainingSeconds()
        val mins = totalSecs / 60
        val secs = totalSecs % 60
        return String.format("%02d:%02d", mins, secs)
    }

    // For testing / simulation purposes only
    fun simulateFastForward(seconds: Int) {
        holdStartEpochMs -= (seconds * 1000L)
    }
}
