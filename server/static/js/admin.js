const dom = {
  trackerForm: document.getElementById("tracker-form"),
  deviceId: document.getElementById("device-id"),
  deviceKey: document.getElementById("device-key"),
  generateKey: document.getElementById("generate-key"),
  trackers: document.getElementById("trackers"),
  routeForm: document.getElementById("route-form"),
  routeFile: document.getElementById("route-file"),
  clearData: document.getElementById("clear-data"),
  message: document.getElementById("admin-message"),
};

function setMessage(text, isError = false) {
  dom.message.textContent = text;
  dom.message.classList.toggle("error", isError);
}

async function fetchTrackers() {
  const response = await fetch("/api/admin/trackers");
  if (!response.ok) {
    throw new Error("Unable to load trackers");
  }
  return response.json();
}

function renderTrackers(rows) {
  if (!rows.length) {
    dom.trackers.innerHTML = "<div class=\"device-values\">No trackers configured.</div>";
    return;
  }

  dom.trackers.innerHTML = rows
    .map((tracker) => {
      const id = String(tracker.device_id || "");
      const key = String(tracker.device_key || "");
      return `
      <div class="tracker-row">
        <div>
          <div class="device-name">${id}</div>
          <div class="device-values">${key}</div>
        </div>
        <button data-remove="${id}" class="danger-btn" type="button">Remove</button>
      </div>
    `;
    })
    .join("");
}

async function refreshTrackers() {
  const payload = await fetchTrackers();
  renderTrackers(Array.isArray(payload.trackers) ? payload.trackers : []);
}

async function createOrUpdateTracker(deviceId, deviceKey) {
  const response = await fetch("/api/admin/trackers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_id: deviceId, device_key: deviceKey || null }),
  });
  if (!response.ok) {
    throw new Error("Failed to save tracker");
  }
  return response.json();
}

async function removeTracker(deviceId) {
  const response = await fetch(`/api/admin/trackers/${encodeURIComponent(deviceId)}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to remove tracker");
  }
}

async function generateKey() {
  const response = await fetch("/api/admin/trackers/generate-key", { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to generate key");
  }
  const data = await response.json();
  return String(data.device_key || "");
}

async function uploadRoute(routeGeojson) {
  const response = await fetch("/api/admin/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ route_geojson: routeGeojson }),
  });
  if (!response.ok) {
    throw new Error("Failed to upload route");
  }
}

async function clearTrackerData() {
  const response = await fetch("/api/admin/data/clear", { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to clear tracker data");
  }
  return response.json();
}

dom.generateKey.addEventListener("click", async () => {
  try {
    dom.deviceKey.value = await generateKey();
    setMessage("Generated a new device key.");
  } catch (error) {
    setMessage(error.message || "Unable to generate key.", true);
  }
});

dom.trackerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const deviceId = dom.deviceId.value.trim();
  const deviceKey = dom.deviceKey.value.trim();
  if (!deviceId) {
    setMessage("Device ID is required.", true);
    return;
  }

  try {
    const result = await createOrUpdateTracker(deviceId, deviceKey);
    dom.deviceId.value = result.device_id || deviceId;
    dom.deviceKey.value = result.device_key || "";
    await refreshTrackers();
    setMessage(`Tracker ${deviceId} saved.`);
  } catch (error) {
    setMessage(error.message || "Unable to save tracker.", true);
  }
});

dom.trackers.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }
  const removeId = target.dataset.remove;
  if (!removeId) {
    return;
  }

  try {
    await removeTracker(removeId);
    await refreshTrackers();
    setMessage(`Removed tracker ${removeId}.`);
  } catch (error) {
    setMessage(error.message || "Unable to remove tracker.", true);
  }
});

dom.routeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = dom.routeFile.files && dom.routeFile.files[0];
  if (!file) {
    setMessage("Please select a route file.", true);
    return;
  }

  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    await uploadRoute(parsed);
    setMessage("Route file uploaded.");
  } catch (error) {
    setMessage(error.message || "Unable to upload route.", true);
  }
});

dom.clearData.addEventListener("click", async () => {
  const confirmed = window.confirm("Delete all tracker GPS points from the database?");
  if (!confirmed) {
    return;
  }

  try {
    const result = await clearTrackerData();
    setMessage(`Deleted ${result.deleted_points || 0} location points.`);
  } catch (error) {
    setMessage(error.message || "Unable to clear tracker data.", true);
  }
});

(async function init() {
  try {
    await refreshTrackers();
    setMessage("Admin panel ready.");
  } catch (error) {
    setMessage(error.message || "Admin panel failed to load.", true);
  }
})();
