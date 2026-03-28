from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_protected_prefix_mismatch_bypasses_csrf(monkeypatch):
    _configure_security_settings(
        monkeypatch, csrf_path_prefixes=["/api/protected-only"]
    )
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={"Origin": "https://evil.example", "Cookie": "session=abc"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
