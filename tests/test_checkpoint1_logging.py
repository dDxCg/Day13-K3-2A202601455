from __future__ import annotations

import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import metrics
from app.logging_config import scrub_event
from app.middleware import CorrelationIdMiddleware
from app.pii import scrub_text


def _middleware_test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(CorrelationIdMiddleware)

    @test_app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"ok": True}

    @test_app.get("/error")
    async def error() -> None:
        raise RuntimeError("boom")

    return test_app


def test_correlation_id_is_generated_or_propagated() -> None:
    with TestClient(_middleware_test_app(), raise_server_exceptions=False) as client:
        generated = client.get("/ok")
        propagated = client.get("/ok", headers={"x-request-id": "upstream-123"})

    assert re.fullmatch(r"req-[0-9a-f]{8}", generated.headers["x-request-id"])
    assert float(generated.headers["x-response-time-ms"]) >= 0
    assert propagated.headers["x-request-id"] == "upstream-123"


def test_correlation_id_is_preserved_on_unhandled_error() -> None:
    with TestClient(_middleware_test_app(), raise_server_exceptions=False) as client:
        response = client.get("/error", headers={"x-request-id": "error-123"})

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "error-123"
    assert response.json()["correlation_id"] == "error-123"


def test_scrubber_covers_all_nested_log_values() -> None:
    event = {
        "session_id": "student@vinuni.edu.vn",
        "payload": {
            "contacts": ["090 123 4567", {"card": "4111 1111 1111 1111"}],
        },
    }

    scrubbed = scrub_event(None, "info", event)

    assert scrubbed["session_id"] == "[REDACTED_EMAIL]"
    assert scrubbed["payload"]["contacts"][0] == "[REDACTED_PHONE_VN]"
    assert scrubbed["payload"]["contacts"][1]["card"] == "[REDACTED_CREDIT_CARD]"


def test_extended_passport_and_address_patterns() -> None:
    output = scrub_text(
        "Passport AB1234567; Địa chỉ: 123 Nguyễn Trãi, Hà Nội; "
        "nhà tại 42 đường Láng, Đống Đa"
    )

    assert "AB1234567" not in output
    assert "123 Nguyễn Trãi" not in output
    assert "42 đường Láng" not in output
    assert "REDACTED_PASSPORT" in output
    assert output.count("REDACTED_ADDRESS_VN") == 2


def test_metrics_snapshot_includes_error_rate(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 3)
    monkeypatch.setattr(metrics, "ERRORS", metrics.Counter({"RuntimeError": 1}))

    result = metrics.snapshot()

    assert result["traffic"] == 4
    assert result["successful_requests"] == 3
    assert result["error_count"] == 1
    assert result["error_rate"] == 0.25
    assert result["error_rate_pct"] == 25.0
