from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_default_protected_prefix_covers_real_backend_route(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = create_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/auth/logout",
            headers={
                "Origin": "https://evil.example",
                "Cookie": "session=abc",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }
