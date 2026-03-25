from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_candidate_token_cannot_access_recruiter_routes(
    async_client, async_session, override_dependencies
):
    await create_recruiter(async_session, email="owner@test.com")
    recruiter = await create_recruiter(async_session, email="owner2@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    token = f"candidate:{cs.invite_email}"
    # Restore real dependency to enforce Auth0 permissions for this test.
    with override_dependencies({get_current_user: security_deps.get_current_user}):
        res = await async_client.get(
            "/api/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code in {401, 403}
