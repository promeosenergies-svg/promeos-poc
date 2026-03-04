"""
PROMEOS — V25: Request Context Middleware tests
Tests X-Request-Id, X-Response-Time, propagation, JSON logging.
"""

import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.request_context import RequestContextMiddleware
from services.json_logger import JsonFormatter, setup_logging


# ── Minimal test app ────────────────────────────────────────────────


def create_test_app():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/slow")
    def slow():
        import time

        time.sleep(0.05)
        return {"status": "slow"}

    return app


app = create_test_app()
client = TestClient(app)


# ── Tests ───────────────────────────────────────────────────────────


class TestRequestContextMiddleware:
    def test_response_contains_x_request_id(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers

    def test_response_contains_x_response_time(self):
        resp = client.get("/health")
        assert "x-response-time" in resp.headers
        assert resp.headers["x-response-time"].endswith("ms")

    def test_client_request_id_is_propagated(self):
        custom_id = "my-custom-id-42"
        resp = client.get("/health", headers={"X-Request-Id": custom_id})
        assert resp.headers["x-request-id"] == custom_id

    def test_request_id_generated_if_absent(self):
        resp = client.get("/health")
        rid = resp.headers["x-request-id"]
        assert len(rid) == 12  # uuid4 hex[:12]

    def test_health_returns_both_headers(self):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
        assert "x-response-time" in resp.headers
        assert resp.json()["status"] == "ok"

    def test_response_time_is_positive(self):
        resp = client.get("/slow")
        time_str = resp.headers["x-response-time"]
        ms = float(time_str.replace("ms", ""))
        assert ms > 0


class TestJsonFormatter:
    def test_json_format_output(self):
        import logging

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="promeos.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc123"
        record.method = "GET"
        record.path = "/health"
        record.status = 200
        record.duration_ms = 5.2
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "info"
        assert parsed["logger"] == "promeos.test"
        assert parsed["message"] == "test message"
        assert parsed["request_id"] == "abc123"
        assert parsed["method"] == "GET"
        assert parsed["status"] == 200
        assert parsed["duration_ms"] == 5.2
        assert "ts" in parsed
