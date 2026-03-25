package org.friends.ksrtracker

import android.content.Context
import org.json.JSONObject

object DeviceConfig {
    private const val PREFS_NAME = "ksr_tracker_prefs"
    private const val PREF_DEVICE_ID = "selected_device_id"
    private const val PREF_DEVICE_KEY_PREFIX = "device_key_"

    fun availableDeviceIds(): List<String> {
        return BuildConfig.TRACKER_DEVICE_IDS_CSV
            .split(",")
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .ifEmpty { listOf("tracker-1") }
    }

    fun deviceKeys(): Map<String, String> {
        val parsed = mutableMapOf<String, String>()
        try {
            val obj = JSONObject(BuildConfig.TRACKER_DEVICE_KEYS_JSON)
            obj.keys().forEach { key ->
                val value = obj.optString(key).trim()
                if (value.isNotEmpty()) {
                    parsed[key] = value
                }
            }
        } catch (_: Exception) {
            // Fallback to single key config when JSON is missing or malformed.
        }

        if (parsed.isEmpty() && BuildConfig.TRACKER_DEVICE_KEY.isNotBlank()) {
            parsed["tracker-1"] = BuildConfig.TRACKER_DEVICE_KEY
        }

        return parsed
    }

    fun selectedDeviceId(context: Context): String {
        val options = availableDeviceIds()
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val saved = prefs.getString(PREF_DEVICE_ID, null)
        return if (saved != null && options.contains(saved)) saved else options.first()
    }

    fun setSelectedDeviceId(context: Context, deviceId: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(PREF_DEVICE_ID, deviceId).apply()
    }

    fun deviceKey(context: Context, deviceId: String): String? {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val saved = prefs.getString(PREF_DEVICE_KEY_PREFIX + deviceId, null)?.trim()
        if (!saved.isNullOrEmpty()) {
            return saved
        }
        return deviceKeys()[deviceId]
    }

    fun setDeviceKey(context: Context, deviceId: String, key: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(PREF_DEVICE_KEY_PREFIX + deviceId, key.trim()).apply()
    }
}
