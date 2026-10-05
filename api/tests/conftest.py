"""Test chạy trên database thật (không mock). Cần đã chạy `make all` trước `make test`."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


def assert_envelope(body: dict) -> list | dict:
    assert set(body) == {"data", "meta"}
    assert {"as_of", "row_count", "source"} <= set(body["meta"])
    if isinstance(body["data"], list):
        assert body["meta"]["row_count"] == len(body["data"])
    return body["data"]
