package org.friends.ksrtracker

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    private lateinit var statusText: TextView
    private lateinit var trackerSpinner: Spinner
    private var deviceIds: List<String> = emptyList()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        val granted = result.values.all { it }
        statusText.text = if (granted) {
            getString(R.string.status_permissions_granted)
        } else {
            getString(R.string.status_permissions_missing)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        trackerSpinner = findViewById(R.id.trackerSpinner)
        setupTrackerSelector()
        findViewById<Button>(R.id.startButton).setOnClickListener {
            val hasPermissions = requestPermissionsIfNeeded()
            if (hasPermissions) {
                val selectedDeviceId = trackerSpinner.selectedItem?.toString() ?: DeviceConfig.selectedDeviceId(this)
                DeviceConfig.setSelectedDeviceId(this, selectedDeviceId)
                ContextCompat.startForegroundService(
                    this,
                    Intent(this, TrackingService::class.java)
                        .setAction(TrackingService.ACTION_START)
                        .putExtra(TrackingService.EXTRA_DEVICE_ID, selectedDeviceId),
                )
                statusText.text = getString(R.string.status_tracking_started, selectedDeviceId)
            }
        }

        findViewById<Button>(R.id.stopButton).setOnClickListener {
            startService(Intent(this, TrackingService::class.java).setAction(TrackingService.ACTION_STOP))
            statusText.text = getString(R.string.status_tracking_stopped)
        }
    }

    private fun setupTrackerSelector() {
        deviceIds = DeviceConfig.availableDeviceIds()
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, deviceIds)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        trackerSpinner.adapter = adapter

        val selected = DeviceConfig.selectedDeviceId(this)
        val selectedIndex = deviceIds.indexOf(selected).coerceAtLeast(0)
        trackerSpinner.setSelection(selectedIndex)
    }

    private fun requestPermissionsIfNeeded(): Boolean {
        val requested = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requested.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val missing = requested.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isEmpty()) {
            return true
        }

        permissionLauncher.launch(missing.toTypedArray())
        statusText.text = getString(R.string.status_permissions_missing)
        return false
    }
}
