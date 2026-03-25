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

let marker = null;
let routeLayer = null;
let reconnectTimer = null;

const dom = {
  connection: document.getElementById("connection-pill"),
  lastTs: document.getElementById("last-ts"),
  lat: document.getElementById("lat"),
  lng: document.getElementById("lng"),
  speed: document.getElementById("speed"),
  progress: document.getElementById("progress"),
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

function moveMarker(lat, lng) {
  if (typeof lat !== "number" || typeof lng !== "number") {
    return;
  }

  if (!marker) {
    marker = L.circleMarker([lat, lng], {
      radius: 8,
      color: "#a8333f",
      fillColor: "#a8333f",
      fillOpacity: 0.9,
      weight: 2,
    }).addTo(map);
    map.setView([lat, lng], 14);
    return;
  }

  marker.setLatLng([lat, lng]);
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
  moveMarker(latest.lat, latest.lng);
  updateStatus({
    lat: latest.lat,
    lng: latest.lng,
    ts_utc: latest.ts_utc,
    speed_kmh: data.stats ? data.stats.speed_kmh : null,
    progress_percent: data.stats ? data.stats.progress_percent : null,
  });
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
    moveMarker(payload.lat, payload.lng);
    updateStatus({
      lat: payload.lat,
      lng: payload.lng,
      ts_utc: payload.ts_utc,
      speed_kmh: typeof payload.speed === "number" ? payload.speed * 3.6 : null,
      progress_percent: null,
    });
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
