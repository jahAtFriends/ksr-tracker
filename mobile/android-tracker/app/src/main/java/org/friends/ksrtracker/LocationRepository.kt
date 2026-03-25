package org.friends.ksrtracker

import kotlinx.coroutines.delay

class LocationRepository(
    private val apiClient: ApiClient,
) {
    private val queue = ArrayDeque<LocationSample>()

    fun enqueue(point: LocationSample) {
        queue.addLast(point)
        if (queue.size > 500) {
            queue.removeFirst()
        }
    }

    suspend fun flushIfNeeded() {
        if (queue.size < BuildConfig.UPLOAD_BATCH_SIZE) {
            return
        }

        flushBatch(minOf(queue.size, 25))
    }

    suspend fun flushAll() {
        while (queue.isNotEmpty()) {
            val sent = flushBatch(minOf(queue.size, 25))
            if (!sent) {
                return
            }
        }
    }

    private suspend fun flushBatch(size: Int): Boolean {
        val batch = mutableListOf<LocationSample>()
        repeat(size) {
            queue.removeFirstOrNull()?.let(batch::add)
        }

        if (batch.isEmpty()) {
            return true
        }

        val ok = apiClient.postPoints(batch)
        if (!ok) {
            // Put points back in front order when upload fails.
            batch.asReversed().forEach { queue.addFirst(it) }
            delay(3_000)
        }
        return ok
    }
}

data class LocationSample(
    val lat: Double,
    val lng: Double,
    val speedMps: Double?,
    val accuracyMeters: Double?,
    val tsIsoUtc: String,
)
