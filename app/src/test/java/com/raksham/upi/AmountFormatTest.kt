package com.raksham.upi

import com.raksham.upi.ui.formatAmount
import com.raksham.upi.ui.groupIndian
import org.junit.Assert.assertEquals
import org.junit.Test

class AmountFormatTest {

    @Test
    fun groupsDigitsTheIndianWay() {
        assertEquals("45", groupIndian("45"))
        assertEquals("450", groupIndian("450"))
        assertEquals("4,500", groupIndian("4500"))
        assertEquals("48,000", groupIndian("48000"))
        assertEquals("1,25,000", groupIndian("125000"))
        assertEquals("12,34,567", groupIndian("1234567"))
    }

    @Test
    fun showsPaiseOnlyWhenPresent() {
        assertEquals("450", formatAmount(450.0))
        assertEquals("48,000", formatAmount(48000.0))
        assertEquals("1,250.50", formatAmount(1250.5))
        assertEquals("0.05", formatAmount(0.05))
    }
}
