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
const deviceColorById = new Map();
const latestPointsByDevice = new Map();
const deviceStatsById = new Map();

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
  latestDevice: document.getElementById("latest-device"),
  lastTs: document.getElementById("last-ts"),
  lat: document.getElementById("lat"),
  lng: document.getElementById("lng"),
  speed: document.getElementById("speed"),
  progress: document.getElementById("progress"),
  deviceList: document.getElementById("device-list"),
};

function setConnectionState(isLive) {
  dom.connection.classList.toggle("live", isLive);
  dom.connection.classList.toggle("stale", !isLive);
  dom.connection.textContent = isLive ? "Live" : "Disconnected";
}

function updateStatus({ lat, lng, ts_utc, speed_kmh, progress_percent }) {
  dom.lastTs.textContent = ts_utc || "-";
  dom.lat.textContent = typeof lat === "number" ? lat.toFixed(6) : "-";
  dom.lng.textContent = typeof lng === "number" ? lng.toFixed(6) : "-";
  dom.speed.textContent = typeof speed_kmh === "number" ? speed_kmh.toFixed(2) : "-";
  dom.progress.textContent = typeof progress_percent === "number" ? `${progress_percent.toFixed(2)}%` : "-";
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
    map.setView([lat, lng], 14);
    return;
  }

  existing.setLatLng([lat, lng]);
}

function renderDeviceList(points, statsByDevice = {}) {
  if (!Array.isArray(points) || points.length === 0) {
    dom.deviceList.innerHTML = "<div class=\"device-values\">No tracker data yet.</div>";
    return;
  }

  const sorted = [...points].sort((a, b) => String(a.device_id).localeCompare(String(b.device_id)));
  dom.deviceList.innerHTML = sorted
    .map((point) => {
      const deviceId = String(point.device_id || "tracker-1");
      const color = colorForDevice(deviceId);
      const speed = statsByDevice[deviceId] ? statsByDevice[deviceId].speed_kmh : null;
      const progress = statsByDevice[deviceId] ? statsByDevice[deviceId].progress_percent : null;
      const speedText = typeof speed === "number" ? `${speed.toFixed(2)} km/h` : "-";
      const progressText = typeof progress === "number" ? `${progress.toFixed(2)}%` : "-";
      return `
        <div class="device-row">
          <div class="device-dot" style="background:${color}"></div>
          <div class="device-meta">
            <div class="device-name">${deviceId}</div>
            <div class="device-values">${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}</div>
            <div class="device-values">${speedText} | ${progressText}</div>
          </div>
        </div>
      `;
    })
    .join("");
}

function refreshDeviceList() {
  const points = Array.from(latestPointsByDevice.values());
  const stats = Object.fromEntries(deviceStatsById.entries());
  renderDeviceList(points, stats);
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
  if (routeLayer.getBounds().isValid()) {
    map.fitBounds(routeLayer.getBounds(), { padding: [20, 20] });
  }
}

async function loadInitialState() {
  const response = await fetch("/api/state/latest");
  if (!response.ok) {
    return;
  }

  const data = await response.json();
  const latest = data.latest || {};
  const latestByDevice = Array.isArray(data.latest_by_device) ? data.latest_by_device : [];
  const statsByDevice = data.stats && data.stats.by_device ? data.stats.by_device : {};

  latestByDevice.forEach((point) => {
    const deviceId = String(point.device_id || "tracker-1");
    moveMarker(deviceId, point.lat, point.lng);
    latestPointsByDevice.set(deviceId, point);
  });

  Object.entries(statsByDevice).forEach(([deviceId, stat]) => {
    deviceStatsById.set(deviceId, stat);
  });

  dom.latestDevice.textContent = latest.device_id || "-";
  updateStatus({
    lat: latest.lat,
    lng: latest.lng,
    ts_utc: latest.ts_utc,
    speed_kmh: data.stats ? data.stats.speed_kmh : null,
    progress_percent: data.stats ? data.stats.progress_percent : null,
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
    latestPointsByDevice.set(deviceId, payload);
    deviceStatsById.set(deviceId, {
      speed_kmh: typeof payload.speed === "number" ? payload.speed * 3.6 : null,
      progress_percent: null,
    });
    dom.latestDevice.textContent = deviceId;
    updateStatus({
      lat: payload.lat,
      lng: payload.lng,
      ts_utc: payload.ts_utc,
      speed_kmh: typeof payload.speed === "number" ? payload.speed * 3.6 : null,
      progress_percent: null,
    });
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
  await loadInitialState();
  connectStream();
})();
