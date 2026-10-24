package com.raksham.risk.session

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CallerCheckTest {
    private val day = 24L * 60 * 60 * 1000

    @Test
    fun aContactSavedDuringTheScamDoesNotCount() {
        assertFalse(CallerCheck.isEstablished(0))
        assertFalse(CallerCheck.isEstablished(6 * day))
    }

    @Test
    fun aContactKeptForAWeekCounts() {
        assertTrue(CallerCheck.isEstablished(7 * day))
        assertTrue(CallerCheck.isEstablished(400 * day))
    }
}
