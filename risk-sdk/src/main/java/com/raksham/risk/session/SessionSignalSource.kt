package com.raksham.risk.session

interface SessionSignalSource {
    fun collectSignals(): SessionSignals
}
