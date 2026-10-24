package com.raksham.risk.session

object SessionSignalSourceProvider {
    private var defaultSource: SessionSignalSource = RealSignalSource()
    private var activeSource: SessionSignalSource? = null

    fun setDefault(source: SessionSignalSource) {
        defaultSource = source
    }

    val current: SessionSignalSource
        get() = activeSource ?: defaultSource

    fun setScriptedSource(scripted: ScriptedSignalSource) {
        activeSource = scripted
    }

    fun restoreRealSource() {
        activeSource = null
    }
}
