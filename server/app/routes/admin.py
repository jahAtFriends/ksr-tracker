from __future__ import annotations

import secrets
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin_auth
from ..db import clear_location_points, delete_tracker, list_trackers, upsert_tracker, write_route_geojson
from ..schemas import RouteUploadRequest, TrackerCreateRequest


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/trackers")
def get_trackers(_: Annotated[None, Depends(require_admin_auth)]) -> dict[str, list[dict[str, str]]]:
    trackers = list_trackers(include_keys=True)
    return {"trackers": trackers}


@router.post("/trackers")
def add_or_update_tracker(
    payload: TrackerCreateRequest,
    _: Annotated[None, Depends(require_admin_auth)],
) -> dict[str, str | bool]:
    device_id = payload.device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")

    device_key = payload.device_key.strip() if payload.device_key else secrets.token_urlsafe(18)
    upsert_tracker(device_id=device_id, device_key=device_key)
    return {"ok": True, "device_id": device_id, "device_key": device_key}


@router.delete("/trackers/{device_id}")
def remove_tracker(
    device_id: str,
    _: Annotated[None, Depends(require_admin_auth)],
) -> dict[str, bool]:
    removed = delete_tracker(device_id)
    return {"ok": removed}


@router.post("/trackers/generate-key")
def generate_key(_: Annotated[None, Depends(require_admin_auth)]) -> dict[str, str]:
    return {"device_key": secrets.token_urlsafe(18)}


@router.post("/route")
def upload_route(
    payload: RouteUploadRequest,
    _: Annotated[None, Depends(require_admin_auth)],
) -> dict[str, str | bool]:
    geojson_type = payload.route_geojson.get("type")
    if geojson_type not in {"FeatureCollection", "Feature"}:
        raise HTTPException(status_code=400, detail="Expected GeoJSON FeatureCollection or Feature")

    write_route_geojson(payload.route_geojson)
    return {"ok": True, "route_path": str(Path("/static/data/route.geojson"))}


@router.post("/data/clear")
def clear_data(_: Annotated[None, Depends(require_admin_auth)]) -> dict[str, int | bool]:
    deleted_points = clear_location_points()
    return {"ok": True, "deleted_points": deleted_points}
