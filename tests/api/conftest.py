from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import DATA_DIR


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    settings = Settings(data_dir=DATA_DIR, git_sha="test-sha", app_env="dev")
    # Entering the context runs the lifespan, i.e. the real fail-fast data load.
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def assert_error(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]
    return dict(error)
