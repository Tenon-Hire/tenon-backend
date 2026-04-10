from __future__ import annotations

import pytest

from tests.shared.middleware.shared_http_csrf_cors_hardening_test_utils import *


@pytest.mark.asyncio
async def test_csrf_middleware_passes_non_http_scopes():
    called = {"value": False}

    async def app(scope, receive, send):
        called["value"] = True

    middleware = middleware_http.CsrfOriginEnforcementMiddleware(
        app,
        allowed_origins=["https://frontend.winoe.ai"],
        protected_path_prefixes=["/api"],
    )
    await middleware({"type": "lifespan"}, lambda: None, lambda _message: None)

    assert called["value"] is True
