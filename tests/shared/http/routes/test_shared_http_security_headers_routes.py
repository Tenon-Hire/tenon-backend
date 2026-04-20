from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_response_includes_media_csp_header(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    csp = response.headers.get("content-security-policy")
    assert csp is not None
    assert "media-src" in csp
    assert "connect-src" in csp
    assert "http://localhost:8000" in csp
