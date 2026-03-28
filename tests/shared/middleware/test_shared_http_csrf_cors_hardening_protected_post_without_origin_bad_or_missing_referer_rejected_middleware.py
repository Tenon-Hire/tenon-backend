from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"Cookie": "session=abc"},
        {"Referer": "https://evil.example/path", "Cookie": "session=abc"},
    ],
)
async def test_protected_post_without_origin_bad_or_missing_referer_rejected(
    monkeypatch, headers
):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/api/demo", headers=headers)

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }
