from __future__ import annotations

from fastapi import APIRouter

from ..db import list_trackers


router = APIRouter(prefix="/api", tags=["trackers"])


@router.get("/trackers")
def get_available_trackers() -> dict[str, list[str]]:
    tracker_rows = list_trackers(include_keys=False)
    ids = [str(row["device_id"]) for row in tracker_rows]
    return {"trackers": ids}
