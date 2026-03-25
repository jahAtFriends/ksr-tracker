from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import require_admin_auth, require_viewer_auth
from .config import settings
from .db import init_db
from .routes.admin import router as admin_router
from .routes.ingest import router as ingest_router
from .routes.state import router as state_router
from .routes.stream import router as stream_router
from .routes.trackers import router as trackers_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="KSR Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin] if settings.allowed_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(state_router)
app.include_router(stream_router)
app.include_router(trackers_router)
app.include_router(admin_router)

static_dir = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index(_: Annotated[None, Depends(require_viewer_auth)]) -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/admin")
def admin_index(_: Annotated[None, Depends(require_admin_auth)]) -> FileResponse:
    return FileResponse(static_dir / "admin.html")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
