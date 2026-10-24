package com.raksham.risk.session

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.provider.ContactsContract
import android.telephony.PhoneNumberUtils
import android.telephony.TelephonyManager
import android.util.Log

/**
 * Is the person on the current call a saved contact? Answered when an incoming call rings, because the
 * app is usually opened mid-call, when the number is no longer available. Only the yes/no answer is kept
 * (on the phone) and sent; the number is never stored or sent.
 *
 * A contact counts only if it was saved (last changed) at least 7 days ago, so a scammer who asks the
 * victim to "save my number first" gains nothing. Outgoing and internet calls have no number here, and
 * without the permissions there is no answer either: both are sent as "not measured", which the server
 * treats like an unknown caller.
 */
class CallerCheckReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return
        val prefs = CallerCheck.prefs(context)
        when (intent.getStringExtra(TelephonyManager.EXTRA_STATE)) {
            TelephonyManager.EXTRA_STATE_RINGING -> {
                if (prefs.getBoolean(CallerCheck.KEY_IN_CALL, false)) {
                    // A second call while one is in progress: we cannot tell which caller the user is
                    // listening to, so neither counts as a saved contact.
                    prefs.edit().putBoolean(CallerCheck.KEY_SAVED, false).apply()
                    return
                }
                // The number arrives only with READ_CALL_LOG; the broadcast without it is ignored.
                @Suppress("DEPRECATION")
                val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER) ?: return
                prefs.edit()
                    .putBoolean(CallerCheck.KEY_SAVED, CallerCheck.isEstablishedContact(context, number))
                    .putLong(CallerCheck.KEY_AT, System.currentTimeMillis())
                    .apply()
            }
            TelephonyManager.EXTRA_STATE_OFFHOOK -> prefs.edit().putBoolean(CallerCheck.KEY_IN_CALL, true).apply()
            TelephonyManager.EXTRA_STATE_IDLE -> prefs.edit().clear().apply()
        }
    }
}

object CallerCheck {
    internal const val KEY_SAVED = "caller_saved"
    internal const val KEY_AT = "checked_at"
    internal const val KEY_IN_CALL = "in_call"
    private const val MIN_CONTACT_AGE_MS = 7L * 24 * 60 * 60 * 1000
    private const val MAX_CALL_MS = 3L * 60 * 60 * 1000

    val PERMISSIONS = arrayOf(
        Manifest.permission.READ_PHONE_STATE,
        Manifest.permission.READ_CALL_LOG,
        Manifest.permission.READ_CONTACTS
    )

    internal fun prefs(context: Context) = context.getSharedPreferences("satark_caller_check", Context.MODE_PRIVATE)

    /** A contact counts once it has gone unchanged for 7 days: saving a number "now" earns no trust. */
    fun isEstablished(contactAgeMs: Long) = contactAgeMs >= MIN_CONTACT_AGE_MS

    fun hasPermissions(context: Context) =
        PERMISSIONS.all { context.checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }

    /** Answer for the phone call in progress, or null if this call was never checked. Only an answered
     *  phone call counts: a number still ringing, or one ringing during an internet call, is not the
     *  person the user is talking to. */
    fun currentCall(context: Context): Boolean? {
        val p = prefs(context)
        val at = p.getLong(KEY_AT, 0L)
        if (!p.getBoolean(KEY_IN_CALL, false)) return null
        if (at == 0L || System.currentTimeMillis() - at > MAX_CALL_MS) return null
        return p.getBoolean(KEY_SAVED, false)
    }

    internal fun isEstablishedContact(context: Context, number: String): Boolean {
        if (context.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) return false
        // Exact match on the normalized number: the phone-lookup URI matches loosely (on some locales only
        // the last digits), which a spoofed number could exploit.
        val iso = (context.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager)
            ?.networkCountryIso?.uppercase()?.ifBlank { null } ?: "IN"
        val e164 = PhoneNumberUtils.formatNumberToE164(number, iso) ?: return false
        return try {
            context.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(ContactsContract.CommonDataKinds.Phone.CONTACT_LAST_UPDATED_TIMESTAMP),
                "${ContactsContract.CommonDataKinds.Phone.NORMALIZED_NUMBER} = ?", arrayOf(e164), null
            )?.use { c ->
                // Every contact holding this number must be established: a fresh copy earns no trust.
                var newest = -1L
                while (c.moveToNext()) newest = maxOf(newest, c.getLong(0))
                if (newest < 0) return false
                val ageMs = System.currentTimeMillis() - newest
                Log.i("CallerCheck", "Caller is a contact last changed ${ageMs / 86_400_000} days ago")  // never the number
                isEstablished(ageMs)
            } ?: false
        } catch (e: Exception) {
            false
        }
    }
}
