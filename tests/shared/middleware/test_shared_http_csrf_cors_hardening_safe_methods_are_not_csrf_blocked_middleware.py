from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_safe_methods_are_not_csrf_blocked(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get(
            "/api/demo",
            headers={"Origin": "https://evil.example", "Cookie": "session=abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
