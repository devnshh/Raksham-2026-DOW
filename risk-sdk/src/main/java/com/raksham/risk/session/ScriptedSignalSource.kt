package com.raksham.risk.session

class ScriptedSignalSource(var signals: SessionSignals) : SessionSignalSource {
    override fun collectSignals(): SessionSignals = signals
}
