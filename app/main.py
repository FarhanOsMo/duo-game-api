"""Application factory and request middleware.

Run locally:  uvicorn app.main:app --reload
"""

import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app import __version__
from app.api import catalog, compute, ops
from app.api.errors import error_response, register_error_handlers
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, request_id_var
from app.core.metrics import DATA_VERSION, IN_FLIGHT, LATENCY, REQUESTS
from app.data.loader import load_game_data

logger = logging.getLogger("app")

# Accept a caller's request id (e.g. from a gateway) only if it is short and plain,
# so it is safe to echo into headers and logs.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# Scrapes of /metrics are excluded from request metrics so the dashboard shows
# client traffic, not Prometheus polling itself every few seconds.
_UNMEASURED = {"/metrics"}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Fail fast: if the data is invalid this raises and the process never
        # starts serving, so a bad export cannot produce wrong answers.
        data = load_game_data(settings.data_dir)
        app.state.game_data = data
        DATA_VERSION.labels(
            data_version=data.manifest.data_version,
            app_version=__version__,
            git_sha=settings.git_sha,
        ).set(1)
        logger.info(
            "data loaded",
            extra={"data_version": data.manifest.data_version, "environment": settings.app_env},
        )
        yield

    app = FastAPI(
        title="Duo Game Data API",
        version=__version__,
        description="Read-only companion API serving the Lanternfall game's exported data "
        "and re-implementing its stat, experience, element and damage formulas.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.started_at = time.monotonic()
    register_error_handlers(app)
    app.include_router(ops.router)
    app.include_router(catalog.router)
    app.include_router(compute.router)

    @app.middleware("http")
    async def observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        IN_FLIGHT.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Last-resort handler: still return the standard error body with a request id
            # (never a stack trace) and still count the 500 in metrics.
            logger.exception("unhandled error")
            response = error_response(500, "internal_error", "internal server error")
        finally:
            IN_FLIGHT.dec()
        elapsed = time.perf_counter() - start
        route = request.scope.get("route")
        # Unmatched paths share one label so random URLs cannot explode cardinality.
        route_label = getattr(route, "path", "unmatched")
        if request.url.path not in _UNMEASURED:
            labels = (request.method, route_label, str(response.status_code))
            REQUESTS.labels(*labels).inc()
            LATENCY.labels(*labels).observe(elapsed)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "route": route_label,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
            },
        )
        request_id_var.reset(token)
        return response

    return app


app = create_app()
