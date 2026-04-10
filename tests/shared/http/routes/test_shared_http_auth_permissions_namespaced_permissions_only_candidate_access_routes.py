from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_namespaced_permissions_only_candidate_access(
    async_client, async_session, monkeypatch, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="namespaced@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)

    def decode(_token: str):
        email_claim = settings.auth.AUTH0_EMAIL_CLAIM
        permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
        return {
            "sub": "auth0|c-ns",
            email_claim: cs.invite_email,
            "email_verified": True,
            permissions_claim: ["candidate:access"],
        }

    monkeypatch.setattr(auth0_module, "decode_auth0_token", decode)
    from app.shared.auth.principal import get_principal

    with override_dependencies({get_principal: security_deps.get_principal}):
        res = await async_client.get(
            f"/api/candidate/session/{cs.token}",
            headers={"Authorization": "Bearer token"},
        )
    assert res.status_code == 200
