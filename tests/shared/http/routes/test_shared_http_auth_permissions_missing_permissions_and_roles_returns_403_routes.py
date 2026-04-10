from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_missing_permissions_and_roles_returns_403(
    async_client, async_session, monkeypatch, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="noperms@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)

    def decode(_token: str):
        email_claim = settings.auth.AUTH0_EMAIL_CLAIM
        return {
            "sub": "auth0|c2",
            email_claim: cs.invite_email,
        }

    monkeypatch.setattr(auth0_module, "decode_auth0_token", decode)
    from app.shared.auth.principal import get_principal

    with override_dependencies({get_principal: security_deps.get_principal}):
        res = await async_client.get(
            f"/api/candidate/session/{cs.token}",
            headers={"Authorization": "Bearer token"},
        )
    assert res.status_code == 403
