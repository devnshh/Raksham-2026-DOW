package com.raksham.risk.session

import org.junit.Assert.assertEquals
import org.junit.Test

/** Same cases as api/tests/test_edge_hunt_batch2.py: the phone and the server must label notes alike. */
class NoteIntentTest {

    @Test
    fun keywordsAreWholeWordsAndScamStoriesWin() {
        assertEquals("refund", NoteIntent.classify("refund for parents"))
        assertEquals("legal", NoteIntent.classify("digital arrest current account"))
        assertEquals("none", NoteIntent.classify("money received thanks"))
        assertEquals("none", NoteIntent.classify("courtyard repair"))
        assertEquals("none", NoteIntent.classify("multitasking class fee"))
        assertEquals("refund", NoteIntent.classify("tasks done, refunds pending"))
        assertEquals("home", NoteIntent.classify("Rent for flat"))
        assertEquals("none", NoteIntent.classify("   "))
        assertEquals("none", NoteIntent.classify(null))
    }
}
