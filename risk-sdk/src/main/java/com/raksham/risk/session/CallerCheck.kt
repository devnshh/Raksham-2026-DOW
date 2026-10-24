package com.raksham.risk.session

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.ContactsContract
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
                // The number arrives only with READ_CALL_LOG; the broadcast without it is ignored.
                @Suppress("DEPRECATION")
                val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER) ?: return
                prefs.edit()
                    .putBoolean(CallerCheck.KEY_SAVED, CallerCheck.isEstablishedContact(context, number))
                    .putLong(CallerCheck.KEY_AT, System.currentTimeMillis())
                    .apply()
            }
            TelephonyManager.EXTRA_STATE_IDLE -> prefs.edit().clear().apply()
        }
    }
}

object CallerCheck {
    internal const val KEY_SAVED = "caller_saved"
    internal const val KEY_AT = "checked_at"
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

    /** Answer for the call in progress, or null if this call was never checked. */
    fun currentCall(context: Context): Boolean? {
        val p = prefs(context)
        val at = p.getLong(KEY_AT, 0L)
        if (at == 0L || System.currentTimeMillis() - at > MAX_CALL_MS) return null
        return p.getBoolean(KEY_SAVED, false)
    }

    internal fun isEstablishedContact(context: Context, number: String): Boolean {
        if (context.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) return false
        // Phone lookup gives the contact's id only; when it was last changed lives in the contacts table.
        val lookup = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number))
        return try {
            val id = context.contentResolver.query(lookup, arrayOf(ContactsContract.PhoneLookup._ID), null, null, null)
                ?.use { c -> if (c.moveToFirst()) c.getLong(0) else null } ?: return false
            val contact = Uri.withAppendedPath(ContactsContract.Contacts.CONTENT_URI, id.toString())
            context.contentResolver.query(
                contact, arrayOf(ContactsContract.Contacts.CONTACT_LAST_UPDATED_TIMESTAMP), null, null, null
            )?.use { c ->
                if (!c.moveToFirst()) return false
                val ageMs = System.currentTimeMillis() - c.getLong(0)
                Log.i("CallerCheck", "Caller is a contact last changed ${ageMs / 86_400_000} days ago")  // never the number
                isEstablished(ageMs)
            } ?: false
        } catch (e: Exception) {
            false
        }
    }
}
