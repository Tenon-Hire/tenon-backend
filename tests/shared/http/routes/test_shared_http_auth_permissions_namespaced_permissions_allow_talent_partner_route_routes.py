from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_namespaced_permissions_allow_talent_partner_route(
    async_client, async_session, monkeypatch, override_dependencies
):
    def decode(_token: str):
        email_claim = settings.auth.AUTH0_EMAIL_CLAIM
        permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
        return {
            "sub": "auth0|r1",
            email_claim: "r@test.com",
            permissions_claim: ["talent_partner:access"],
        }

    monkeypatch.setattr(auth0_module, "decode_auth0_token", decode)
    await create_talent_partner(async_session, email="r@test.com")
    with override_dependencies({get_current_user: security_deps.get_current_user}):
        res = await async_client.get(
            "/api/trials",
            headers={"Authorization": "Bearer token"},
        )
    assert res.status_code == 200
