import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import _game_data
from app.core.config import Settings
from app.data.errors import DataValidationError
from app.main import create_app
from tests.api.conftest import assert_error
from tests.conftest import DATA_DIR


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_reports_data_version(client: TestClient) -> None:
    body = client.get("/ready").json()
    assert body["status"] == "ready"
    assert len(body["data_version"]) == 12


def test_ready_is_503_before_data_loads() -> None:
    # Without the context manager the lifespan (data load) never runs.
    app = create_app(Settings(data_dir=DATA_DIR))
    assert_error(TestClient(app).get("/ready"), 503, "not_ready")


def test_meta(client: TestClient) -> None:
    body = client.get("/api/v1/meta").json()
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert body["app_version"] == "1.0.0"
    assert body["git_sha"] == "test-sha"
    assert body["environment"] == "dev"
    assert body["data"]["version"] == manifest["data_version"]
    assert body["data"]["content_sha256"] == manifest["content_sha256"]
    assert "monsters.json" in body["data"]["files"]
    assert body["uptime_seconds"] >= 0


def test_metrics_expose_request_and_custom_metrics(client: TestClient) -> None:
    client.get("/api/v1/monsters/mon_placeholder_a")
    text = client.get("/metrics").text
    assert 'route="/api/v1/monsters/{monster_id}"' in text
    assert "http_request_duration_seconds_bucket" in text
    assert "http_requests_in_flight" in text
    assert "data_version_info{" in text
    assert "damage_calculations_total" in text
    assert 'route="/metrics"' not in text


def test_request_id_is_generated_and_echoed(client: TestClient) -> None:
    generated = client.get("/health").headers["X-Request-ID"]
    assert len(generated) == 32
    echoed = client.get("/health", headers={"X-Request-ID": "trace-abc.123"})
    assert echoed.headers["X-Request-ID"] == "trace-abc.123"
    unsafe = client.get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert unsafe.headers["X-Request-ID"] != "bad id with spaces"


def test_unknown_route_and_wrong_method_use_error_body(client: TestClient) -> None:
    assert_error(client.get("/api/v1/nope"), 404, "not_found")
    assert_error(client.delete("/api/v1/monsters"), 405, "method_not_allowed")


def test_unhandled_exception_returns_500_body() -> None:
    def boom() -> None:
        raise RuntimeError("simulated failure")

    app = create_app(Settings(data_dir=DATA_DIR))
    app.dependency_overrides[_game_data] = boom
    with TestClient(app) as client:
        error = assert_error(client.get("/api/v1/monsters"), 500, "internal_error")
    assert "simulated" not in error["message"]


def test_startup_fails_fast_on_invalid_data(data_copy: Path) -> None:
    (data_copy / "monsters.json").write_text("{not json", encoding="utf-8")
    app = create_app(Settings(data_dir=data_copy))
    with pytest.raises(DataValidationError, match=r"monsters\.json"), TestClient(app):
        pass
