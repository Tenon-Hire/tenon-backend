from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_candidate_current_task_requires_auth(
    async_client, async_session, override_dependencies
):
    recruiter = await create_recruiter(async_session, email="authcheck@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    from app.shared.auth import dependencies as security_deps
    from app.shared.auth.principal import get_principal

    with override_dependencies({get_principal: security_deps.get_principal}):
        res = await async_client.get(
            f"/api/candidate/session/{cs.id}/current_task",
            headers={"x-candidate-session-id": str(cs.id)},
        )
    assert res.status_code == 401
