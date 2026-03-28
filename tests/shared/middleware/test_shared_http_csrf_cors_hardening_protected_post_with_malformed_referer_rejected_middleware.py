from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_protected_post_with_malformed_referer_rejected(monkeypatch):
    _configure_security_settings(monkeypatch)
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/demo",
            headers={"Referer": "::::", "Cookie": "session=abc"},
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": "CSRF_ORIGIN_MISMATCH",
        "message": "Request origin not allowed.",
    }
