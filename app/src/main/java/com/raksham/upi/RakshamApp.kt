package com.raksham.upi

import android.app.Application
import com.raksham.risk.RiskGate
import com.raksham.risk.session.RealSignalSource
import com.raksham.risk.session.SessionSignalSourceProvider
import com.raksham.risk.session.SessionTracker

class RakshamApp : Application() {

    override fun onCreate() {
        super.onCreate()
        RiskGate.setBaseUrl(BuildConfig.RISK_API_BASE_URL)
        SessionTracker.install(this)
        SessionSignalSourceProvider.setDefault(RealSignalSource(this))
    }
}
