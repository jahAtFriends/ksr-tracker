package org.friends.ksrtracker

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.os.Build
import android.os.IBinder
import androidx.core.content.ContextCompat
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.time.Instant

class TrackingService : Service() {
    private val serviceScope = CoroutineScope(Dispatchers.IO + Job())
    private lateinit var repository: LocationRepository
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var flushJob: Job? = null
    private var isTracking = false
    private var activeDeviceId: String = "tracker-1"

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            result.locations.forEach { location ->
                onLocationReceived(location)
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        activeDeviceId = DeviceConfig.selectedDeviceId(this)
        repository = LocationRepository(ApiClient(this), activeDeviceId)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val selected = intent.getStringExtra(EXTRA_DEVICE_ID)
                if (!selected.isNullOrBlank() && selected != activeDeviceId) {
                    activeDeviceId = selected
                    repository = LocationRepository(ApiClient(this), activeDeviceId)
                }
                startTracking()
            }
            ACTION_STOP -> stopTracking()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
        } catch (_: Exception) {
            // Ignore teardown failures during process shutdown.
        }
        serviceScope.cancel()
        super.onDestroy()
    }

    private fun startTracking() {
        if (isTracking) {
            return
        }
        startForeground(NOTIFICATION_ID, buildNotification("Tracking active: $activeDeviceId"))
        isTracking = true
        startLocationUpdates()
        startFlushLoop()
    }

    private fun startLocationUpdates() {
        if (!hasLocationPermission()) {
            stopTracking()
            return
        }

        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            BuildConfig.LOCATION_INTERVAL_MS,
        )
            .setMinUpdateIntervalMillis(BuildConfig.LOCATION_FASTEST_MS)
            .setWaitForAccurateLocation(false)
            .build()

        fusedLocationClient.requestLocationUpdates(
            request,
            locationCallback,
            mainLooper,
        )
    }

    private fun startFlushLoop() {
        flushJob?.cancel()
        flushJob = serviceScope.launch {
            while (isTracking) {
                repository.flushIfNeeded()
                delay(BuildConfig.LOCATION_INTERVAL_MS)
            }
        }
    }

    private fun onLocationReceived(location: Location) {
        val point = LocationSample(
            lat = location.latitude,
            lng = location.longitude,
            speedMps = if (location.hasSpeed()) location.speed.toDouble() else null,
            accuracyMeters = if (location.hasAccuracy()) location.accuracy.toDouble() else null,
            tsIsoUtc = Instant.ofEpochMilli(location.time).toString(),
        )
        repository.enqueue(point)
    }

    private fun hasLocationPermission(): Boolean {
        val fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        return fine || coarse
    }

    private fun stopTracking() {
        isTracking = false
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
        } catch (_: Exception) {
            // Ignore if updates were never started.
        }
        flushJob?.cancel()
        flushJob = null

        serviceScope.launch {
            repository.flushAll()
        }

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun buildNotification(content: String): Notification {
        createChannelIfNeeded()
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("KSR Tracker")
            .setContentText(content)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .build()
    }

    private fun createChannelIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }
        val channel = NotificationChannel(
            CHANNEL_ID,
            "KSR Tracking",
            NotificationManager.IMPORTANCE_LOW,
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val ACTION_START = "org.friends.ksrtracker.action.START"
        const val ACTION_STOP = "org.friends.ksrtracker.action.STOP"
        const val EXTRA_DEVICE_ID = "org.friends.ksrtracker.extra.DEVICE_ID"
        private const val CHANNEL_ID = "ksr-tracking"
        private const val NOTIFICATION_ID = 1001
    }
}
