package org.friends.ksrtracker

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private lateinit var statusText: TextView
    private lateinit var trackerSpinner: Spinner
    private lateinit var deviceKeyInput: EditText
    private var deviceIds: List<String> = emptyList()
    private val apiClient by lazy { ApiClient(this) }

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
        deviceKeyInput = findViewById(R.id.deviceKeyInput)
        setupTrackerSelector()
        findViewById<Button>(R.id.refreshTrackersButton).setOnClickListener {
            refreshTrackersFromApi()
        }
        findViewById<Button>(R.id.startButton).setOnClickListener {
            val hasPermissions = requestPermissionsIfNeeded()
            if (hasPermissions) {
                val selectedDeviceId = trackerSpinner.selectedItem?.toString() ?: DeviceConfig.selectedDeviceId(this)
                val enteredKey = deviceKeyInput.text.toString().trim()
                if (enteredKey.isEmpty()) {
                    statusText.text = getString(R.string.status_missing_device_key)
                    return@setOnClickListener
                }

                DeviceConfig.setSelectedDeviceId(this, selectedDeviceId)
                DeviceConfig.setDeviceKey(this, selectedDeviceId, enteredKey)
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

        refreshTrackersFromApi()
    }

    private fun setupTrackerSelector(sourceIds: List<String>? = null) {
        val nextDeviceIds = sourceIds?.filter { it.isNotBlank() }?.ifEmpty { null } ?: DeviceConfig.availableDeviceIds()
        deviceIds = nextDeviceIds
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, deviceIds)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        trackerSpinner.adapter = adapter

        val selected = DeviceConfig.selectedDeviceId(this)
        val selectedIndex = deviceIds.indexOf(selected).coerceAtLeast(0)
        trackerSpinner.setSelection(selectedIndex)
        trackerSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                val selectedId = deviceIds.getOrNull(position) ?: return
                DeviceConfig.setSelectedDeviceId(this@MainActivity, selectedId)
                val key = DeviceConfig.deviceKey(this@MainActivity, selectedId).orEmpty()
                deviceKeyInput.setText(key)
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {
                // Keep existing value.
            }
        }

        val currentId = deviceIds.getOrNull(selectedIndex)
        val currentKey = currentId?.let { DeviceConfig.deviceKey(this, it) }.orEmpty()
        deviceKeyInput.setText(currentKey)
    }

    private fun refreshTrackersFromApi() {
        lifecycleScope.launch {
            val remoteTrackers = withContext(Dispatchers.IO) {
                apiClient.fetchTrackers()
            }
            if (!remoteTrackers.isNullOrEmpty()) {
                setupTrackerSelector(remoteTrackers)
                statusText.text = getString(R.string.status_trackers_loaded)
            } else {
                setupTrackerSelector()
                statusText.text = getString(R.string.status_trackers_fallback)
            }
        }
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
