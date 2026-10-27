"""Operational endpoints for orchestrators, Prometheus and humans."""

import time
from typing import Any

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import __version__
from app.api.deps import GameDataDep
from app.api.errors import error_response
from app.data.manifest import DATA_FILES

router = APIRouter(tags=["operations"])


@router.get("/health", summary="Liveness: the process is up")
def health() -> dict[str, str]:
    # Deliberately does no work: a liveness probe that touched dependencies would
    # restart a healthy process whenever something else misbehaved.
    return {"status": "ok"}


@router.get("/ready", summary="Readiness: game data is loaded and serving", response_model=None)
def ready(request: Request) -> dict[str, str] | Response:
    data = getattr(request.app.state, "game_data", None)
    if data is None:
        return error_response(503, "not_ready", "game data is not loaded")
    return {"status": "ready", "data_version": data.manifest.data_version}


@router.get("/metrics", summary="Prometheus metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/api/v1/meta", summary="Build, data version and uptime")
def meta(request: Request, data: GameDataDep) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "app_version": __version__,
        "git_sha": settings.git_sha,
        "environment": settings.app_env,
        "data": {
            "version": data.manifest.data_version,
            "content_sha256": data.manifest.content_sha256,
            "files": list(DATA_FILES),
        },
        "uptime_seconds": round(time.monotonic() - request.app.state.started_at, 3),
    }
