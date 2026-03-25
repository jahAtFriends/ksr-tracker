package org.friends.ksrtracker

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class ApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    fun postPoints(points: List<LocationSample>, deviceId: String): Boolean {
        if (points.isEmpty()) {
            return true
        }

        val deviceKey = DeviceConfig.deviceKeys()[deviceId] ?: return false

        val payload = JSONObject()
            .put("session_id", BuildConfig.TRACKER_SESSION_ID)
            .put("device_id", deviceId)
            .put("batch_id", java.util.UUID.randomUUID().toString())
            .put("points", JSONArray().apply {
                points.forEach { point ->
                    put(
                        JSONObject()
                            .put("lat", point.lat)
                            .put("lng", point.lng)
                            .put("speed", point.speedMps)
                            .put("acc", point.accuracyMeters)
                            .put("ts", point.tsIsoUtc)
                    )
                }
            })

        val request = Request.Builder()
            .url(BuildConfig.TRACKER_BASE_URL + "/api/ingest")
            .addHeader("X-Device-Key", deviceKey)
            .post(payload.toString().toRequestBody(JSON_MEDIA))
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (_: IOException) {
            false
        }
    }

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    }
}
