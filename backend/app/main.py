from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api._registry import register_all_routers
from app.core.config import settings
from app.services.project_workspace_service import PROJECT_STORAGE_DIR

app = FastAPI(
    title="Render Factory API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://frontend:3000",
        settings.public_base_url.rstrip("/"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_storage_dir = PROJECT_STORAGE_DIR.parent
_storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(_storage_dir)), name="storage")

_artifacts_dir = Path("/app/artifacts")
_artifacts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(_artifacts_dir)), name="artifacts")

register_all_routers(app)


@app.get("/", tags=["root"])
async def root() -> dict[str, object]:
    return {
        "ok": True,
        "service": "render_factory_api",
        "env": settings.app_env,
        "docs_url": "/docs",
        "health_url": "/healthz",
    }


@app.get("/metrics")
async def metrics_alias():
    from app.db.session import SessionLocal
    from fastapi.responses import PlainTextResponse
    from app.services.observability_metrics import collect_status_snapshot, export_prometheus_text

    db = SessionLocal()
    try:
        snapshot = collect_status_snapshot(db)
        return PlainTextResponse(export_prometheus_text(snapshot), media_type="text/plain; version=0.0.4")
    finally:
        db.close()
