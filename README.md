# KSR 2026 Tracker (MVP)

This repository includes:

- Python backend for ingest + live updates
- Web map for live race viewing
- Full Android Studio tracker app project
- GPX-to-GeoJSON route conversion utility

## Stack

- Backend: FastAPI + SQLite + SSE
- Web map: Leaflet + OpenStreetMap
- Mobile tracker: Kotlin + FusedLocationProviderClient

## Quick Start (Backend + Web)

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r server/requirements.txt
```

3. Copy `.env.example` to `.env` and set values:
  - `DEVICE_KEYS` for per-device upload authentication (format: `tracker-1:key1,tracker-2:key2`)
  - Optional `DEVICE_KEY` fallback for single-device mode
  - Optional `VIEWER_USERNAME` and `VIEWER_PASSWORD` for web viewer gate
4. Run the API:

```bash
uvicorn server.app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Open:
- `http://localhost:8000/` for the map
- `http://localhost:8000/health` for health

## Core API

- `POST /api/ingest`
- `GET /api/state/latest`
- `GET /api/route`
- `GET /api/stream` (SSE)

Viewer-facing endpoints (`/`, `/api/route`, `/api/state/latest`, `/api/stream`) are protected by HTTP Basic auth when `VIEWER_PASSWORD` is set.

## Example Ingest Call

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -H "X-Device-Key: replace-with-strong-random-token" \
  -d '{
    "session_id": "race-2026",
    "device_id": "tracker-1",
    "batch_id": "test-batch-1",
    "points": [
      {"lat": 39.3314, "lng": -76.6199, "acc": 6.2, "speed": 1.2, "ts": "2026-03-12T12:00:00Z"}
    ]
  }'
```

## Deployment Notes

- Systemd unit template: `ops/systemd/tracker-api.service`
- Nginx reverse proxy template: `ops/nginx/tracker.conf`

## Android App

1. Open [mobile/android-tracker](mobile/android-tracker) in Android Studio.
2. Edit [mobile/android-tracker/app/build.gradle.kts](mobile/android-tracker/app/build.gradle.kts) and set:
  - `TRACKER_BASE_URL`
  - `TRACKER_DEVICE_IDS_CSV`
  - `TRACKER_DEVICE_KEYS_JSON`
  - `TRACKER_SESSION_ID`
3. Connect your Android phone and run the app.
4. In the app, pick the tracker number before pressing Start Tracking.

## Route Import Utility

Convert GPX to route GeoJSON used by the map:

```bash
python tools/gpx_to_geojson.py my-route.gpx server/static/data/route.geojson --name "2026 Kinetic Route"
```

If GPX has many points, thin it:

```bash
python tools/gpx_to_geojson.py my-route.gpx server/static/data/route.geojson --stride 3
```
