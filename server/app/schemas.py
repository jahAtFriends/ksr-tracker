from typing import Optional
from pydantic import BaseModel, Field


class LocationPointIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    acc: Optional[float] = Field(default=None, ge=0)
    speed: Optional[float] = Field(default=None, ge=0)
    ts: Optional[str] = None


class IngestRequest(BaseModel):
    session_id: str = Field(default="race-2026")
    device_id: str = Field(default="tracker-1", min_length=1, max_length=64)
    batch_id: Optional[str] = None
    points: list[LocationPointIn] = Field(min_length=1, max_length=200)
