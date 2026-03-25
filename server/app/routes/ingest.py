from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from ..db import get_device_key, get_latest_point, insert_points
from ..schemas import IngestRequest
from ..sse import broker


router = APIRouter(prefix="/api", tags=["ingest"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_ts(value: str | None) -> str:
    if not value:
        return _utc_now_iso()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


@router.post("/ingest")
async def ingest_location(payload: IngestRequest, x_device_key: str = Header(default="")) -> dict[str, Any]:
    expected_key = get_device_key(payload.device_id)
    if not expected_key or x_device_key.strip() != expected_key:
        raise HTTPException(status_code=401, detail="Invalid device key")

    received_utc = _utc_now_iso()
    rows: list[dict[str, Any]] = []
    for point in payload.points:
        rows.append(
            {
                "lat": point.lat,
                "lng": point.lng,
                "acc": point.acc,
                "speed": point.speed,
                "ts_utc": _normalize_ts(point.ts),
                "received_utc": received_utc,
            }
        )

    inserted = insert_points(payload.session_id, payload.device_id, payload.batch_id, rows)
    latest = get_latest_point(payload.session_id)
    if latest:
        await broker.publish({"event": "location", "payload": latest})

    return {
        "ok": True,
        "inserted": inserted,
        "latest": latest,
    }
