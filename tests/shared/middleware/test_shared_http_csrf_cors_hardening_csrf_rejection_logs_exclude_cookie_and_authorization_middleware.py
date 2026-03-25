from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_csrf_rejection_logs_exclude_cookie_and_authorization(
    monkeypatch, caplog: pytest.LogCaptureFixture
):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()
    caplog.set_level(
        logging.WARNING, logger="app.shared.http.shared_http_middleware_http_middleware"
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Origin": "https://evil.example",
                "Cookie": "session=abc",
                "Authorization": "Bearer integration-test-token",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }
    assert "session=abc" not in caplog.text
    assert "integration-test-token" not in caplog.text

    record = next(
        record for record in caplog.records if record.message == "csrf_origin_mismatch"
    )
    assert not hasattr(record, "cookie")
    assert not hasattr(record, "authorization")
