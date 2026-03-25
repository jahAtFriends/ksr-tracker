const map = L.map("map", { zoomControl: true }).setView([39.3314, -76.6199], 13);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const routeStyle = {
  color: "#1f7a8c",
  weight: 5,
  opacity: 0.8,
};

let routeLayer = null;
let reconnectTimer = null;
const markersByDevice = new Map();
const pathLayerByDevice = new Map();
const pathPointsByDevice = new Map();
const lastPointTsByDevice = new Map();
const deviceColorById = new Map();
const latestPointsByDevice = new Map();

const palette = [
  "#a8333f",
  "#1f7a8c",
  "#2d6a4f",
  "#bc6c25",
  "#3d5a80",
  "#8d5a97",
  "#6c757d",
  "#ef476f",
];

const dom = {
  connection: document.getElementById("connection-pill"),
  deviceList: document.getElementById("device-list"),
};

function setConnectionState(isLive) {
  dom.connection.classList.toggle("live", isLive);
  dom.connection.classList.toggle("stale", !isLive);
  dom.connection.textContent = isLive ? "Live" : "Disconnected";
}

function colorForDevice(deviceId) {
  if (!deviceColorById.has(deviceId)) {
    const nextColor = palette[deviceColorById.size % palette.length];
    deviceColorById.set(deviceId, nextColor);
  }
  return deviceColorById.get(deviceId);
}

function moveMarker(deviceId, lat, lng) {
  if (typeof lat !== "number" || typeof lng !== "number") {
    return;
  }

  const color = colorForDevice(deviceId);
  const existing = markersByDevice.get(deviceId);
  if (!existing) {
    const marker = L.circleMarker([lat, lng], {
      radius: 8,
      color,
      fillColor: color,
      fillOpacity: 0.9,
      weight: 2,
    }).addTo(map);
    markersByDevice.set(deviceId, marker);
    return;
  }

  existing.setLatLng([lat, lng]);
}

function appendPathPoint(deviceId, lat, lng, tsUtc) {
  if (typeof lat !== "number" || typeof lng !== "number") {
    return;
  }

  const nextTs = tsUtc || "";
  const lastTs = lastPointTsByDevice.get(deviceId) || "";
  if (nextTs && lastTs && nextTs <= lastTs) {
    return;
  }

  const points = pathPointsByDevice.get(deviceId) || [];
  points.push([lat, lng]);
  if (points.length > 5000) {
    points.shift();
  }
  pathPointsByDevice.set(deviceId, points);

  const color = colorForDevice(deviceId);
  let layer = pathLayerByDevice.get(deviceId);
  if (!layer) {
    layer = L.polyline(points, {
      color,
      weight: 4,
      opacity: 0.75,
    }).addTo(map);
    pathLayerByDevice.set(deviceId, layer);
  } else {
    layer.setLatLngs(points);
  }

  if (nextTs) {
    lastPointTsByDevice.set(deviceId, nextTs);
  }
}

function seedPathsFromHistory(points) {
  const ordered = [...points].sort((a, b) => String(a.ts_utc || "").localeCompare(String(b.ts_utc || "")));
  ordered.forEach((point) => {
    const deviceId = String(point.device_id || "tracker-1");
    appendPathPoint(deviceId, point.lat, point.lng, point.ts_utc);
  });
}

function speedTextForPoint(point) {
  if (!point || typeof point.speed !== "number") {
    return "-";
  }
  return `${(point.speed * 3.6).toFixed(2)} km/h`;
}

function renderDeviceList(points) {
  if (!Array.isArray(points) || points.length === 0) {
    dom.deviceList.innerHTML = "<div class=\"device-values\">No tracker data yet.</div>";
    return;
  }

  const sorted = [...points].sort((a, b) => String(a.device_id).localeCompare(String(b.device_id)));
  dom.deviceList.innerHTML = sorted
    .map((point) => {
      const deviceId = String(point.device_id || "tracker-1");
      const color = colorForDevice(deviceId);
      const lat = typeof point.lat === "number" ? point.lat.toFixed(5) : "-";
      const lng = typeof point.lng === "number" ? point.lng.toFixed(5) : "-";
      const speedText = speedTextForPoint(point);
      const updatedText = point.ts_utc || "-";
      return `
        <div class="device-row">
          <div class="device-dot" style="background:${color}"></div>
          <div class="device-meta">
            <div class="device-name">${deviceId}</div>
            <div class="device-values device-field"><span class="device-label">Location</span><span>${lat}, ${lng}</span></div>
            <div class="device-values device-field"><span class="device-label">Speed</span><span>${speedText}</span></div>
            <div class="device-values device-field"><span class="device-label">Updated</span><span>${updatedText}</span></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function refreshDeviceList() {
  const points = Array.from(latestPointsByDevice.values());
  renderDeviceList(points);
}

async function loadRoute() {
  const response = await fetch("/api/route");
  if (!response.ok) {
    return;
  }
  const route = await response.json();
  if (routeLayer) {
    map.removeLayer(routeLayer);
  }
  routeLayer = L.geoJSON(route, { style: routeStyle }).addTo(map);
  // Keep viewport centered on the route geometry whenever route data is available.
  if (routeLayer.getBounds().isValid()) {
    map.fitBounds(routeLayer.getBounds(), { padding: [20, 20] });
  }
}

async function loadRecentHistory() {
  const response = await fetch("/api/state/recent?limit=5000");
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  const points = Array.isArray(data.points) ? data.points : [];
  seedPathsFromHistory(points);
}

async function loadInitialState() {
  const response = await fetch("/api/state/latest");
  if (!response.ok) {
    return;
  }

  const data = await response.json();
  const latestByDevice = Array.isArray(data.latest_by_device) ? data.latest_by_device : [];

  latestByDevice.forEach((point) => {
    const deviceId = String(point.device_id || "tracker-1");
    moveMarker(deviceId, point.lat, point.lng);
    appendPathPoint(deviceId, point.lat, point.lng, point.ts_utc);
    latestPointsByDevice.set(deviceId, point);
  });

  refreshDeviceList();
}

function connectStream() {
  const source = new EventSource("/api/stream");

  source.addEventListener("open", () => {
    setConnectionState(true);
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  });

  source.addEventListener("location", (event) => {
    const payload = JSON.parse(event.data);
    const deviceId = String(payload.device_id || "tracker-1");
    moveMarker(deviceId, payload.lat, payload.lng);
    appendPathPoint(deviceId, payload.lat, payload.lng, payload.ts_utc);
    latestPointsByDevice.set(deviceId, payload);
    refreshDeviceList();
  });

  source.addEventListener("heartbeat", () => {
    setConnectionState(true);
  });

  source.onerror = () => {
    setConnectionState(false);
    source.close();
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(connectStream, 2500);
    }
  };
}

window.addEventListener("resize", () => {
  map.invalidateSize();
});

(async function init() {
  setConnectionState(false);
  await loadRoute();
  await loadRecentHistory();
  await loadInitialState();
  connectStream();
})();
