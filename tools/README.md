# Route Utilities

## GPX to GeoJSON

Convert a GPX track or route into a GeoJSON LineString for the web map.

```bash
python tools/gpx_to_geojson.py input.gpx server/static/data/route.geojson --name "2026 Kinetic Race Route"
```

Optional thinning if GPX has many points:

```bash
python tools/gpx_to_geojson.py input.gpx server/static/data/route.geojson --stride 3
```

Notes:
- GeoJSON coordinates are written as `[longitude, latitude]`.
- If both track and route points exist, track points are preferred.
