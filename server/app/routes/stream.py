from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth import require_viewer_auth
from ..sse import broker


router = APIRouter(prefix="/api", tags=["stream"])


def _format_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get("/stream")
async def stream_updates(
    _: Annotated[None, Depends(require_viewer_auth)],
    session_id: str = "race-2026",
) -> StreamingResponse:
    queue = broker.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    payload = {
                        **message.get("payload", {}),
                        "session_id": session_id,
                    }
                    yield _format_sse(message.get("event", "message"), payload)
                except asyncio.TimeoutError:
                    yield _format_sse(
                        "heartbeat",
                        {"ts_utc": datetime.now(timezone.utc).isoformat(), "session_id": session_id},
                    )
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
