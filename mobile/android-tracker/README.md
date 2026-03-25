# Android Tracker App

This folder now contains a complete Android Studio project for the tracker app.

## What Is Included

- Kotlin app with foreground `TrackingService`
- Real GPS updates using `FusedLocationProviderClient`
- Batched uploads to backend ingest endpoint
- Runtime permission handling for location and notifications
- Basic Start/Stop UI

## Configure Before Running

Edit [app/build.gradle.kts](app/build.gradle.kts) and update these fields in `defaultConfig`:

- `TRACKER_BASE_URL`
- `TRACKER_DEVICE_KEY`
- `TRACKER_SESSION_ID`

## Run In Android Studio

1. Open [mobile/android-tracker](mobile/android-tracker) as a project in Android Studio.
2. Let Gradle sync and download dependencies.
3. Connect your phone via USB debugging.
4. Build and run the `app` configuration.
5. Grant requested permissions and press **Start Tracking**.

## Notes

- Minimum SDK is 26.
- For local development over HTTP, use HTTPS tunnel or set a debug-only cleartext config.
- Current queue is in-memory; if the app is killed, unsent points are lost.

## Upload Contract

POST `/api/ingest`

Headers:
- `X-Device-Key: <shared-secret>`

Body:

```json
{
  "session_id": "race-2026",
  "batch_id": "uuid-string",
  "points": [
    {
      "lat": 39.33,
      "lng": -76.61,
      "acc": 6.0,
      "speed": 1.8,
      "ts": "2026-03-12T15:04:05Z"
    }
  ]
}
```
