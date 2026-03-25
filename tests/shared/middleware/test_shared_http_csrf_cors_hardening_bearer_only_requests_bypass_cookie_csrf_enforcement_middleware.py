from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_bearer_only_requests_bypass_cookie_csrf_enforcement(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={
                "Authorization": "Bearer integration-test-token",
                "Origin": "https://evil.example",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
