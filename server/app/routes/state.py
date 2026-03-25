from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..auth import require_viewer_auth
from ..config import settings
from ..db import get_latest_point


router = APIRouter(prefix="/api", tags=["state"])


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _load_route_geojson(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_line_coords(route_geojson: dict[str, Any]) -> list[tuple[float, float]]:
    for feature in route_geojson.get("features", []):
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "LineString":
            coords = geometry.get("coordinates", [])
            return [(float(lat_lng[1]), float(lat_lng[0])) for lat_lng in coords if len(lat_lng) >= 2]
    return []


def _route_progress_percent(lat: float, lng: float, route_points: list[tuple[float, float]]) -> float | None:
    if len(route_points) < 2:
        return None

    distances = [0.0]
    for idx in range(1, len(route_points)):
        prev_lat, prev_lng = route_points[idx - 1]
        cur_lat, cur_lng = route_points[idx]
        distances.append(distances[-1] + _haversine_m(prev_lat, prev_lng, cur_lat, cur_lng))

    total_m = distances[-1]
    if total_m <= 0:
        return None

    nearest_idx = min(
        range(len(route_points)),
        key=lambda i: _haversine_m(lat, lng, route_points[i][0], route_points[i][1]),
    )
    return round((distances[nearest_idx] / total_m) * 100, 2)


@router.get("/route")
def get_route(_: Annotated[None, Depends(require_viewer_auth)]) -> dict[str, Any]:
    return _load_route_geojson(settings.route_path)


@router.get("/state/latest")
def get_latest_state(
    _: Annotated[None, Depends(require_viewer_auth)],
    session_id: str = "race-2026",
) -> dict[str, Any]:
    latest = get_latest_point(session_id)
    route_geojson = _load_route_geojson(settings.route_path)
    route_points = _extract_line_coords(route_geojson)

    progress_percent = None
    if latest and route_points:
        progress_percent = _route_progress_percent(float(latest["lat"]), float(latest["lng"]), route_points)

    speed_kmh = None
    if latest and latest.get("speed") is not None:
        speed_kmh = round(float(latest["speed"]) * 3.6, 2)

    return {
        "session_id": session_id,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "latest": latest,
        "stats": {
            "speed_kmh": speed_kmh,
            "progress_percent": progress_percent,
        },
    }
