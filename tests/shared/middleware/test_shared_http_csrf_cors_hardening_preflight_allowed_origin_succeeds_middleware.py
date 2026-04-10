from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_preflight_allowed_origin_succeeds(monkeypatch):
    _configure_security_settings(monkeypatch, env="prod")
    app = _csrf_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.options(
            "/api/demo",
            headers={
                "Origin": "https://frontend.winoe.ai",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "https://frontend.winoe.ai"
    )
