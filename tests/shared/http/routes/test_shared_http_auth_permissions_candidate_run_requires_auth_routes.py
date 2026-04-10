from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_candidate_run_requires_auth(
    async_client, async_session, override_dependencies
):
    talent_partner = await create_talent_partner(async_session, email="auth3@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    task_id = tasks[0].id

    from app.shared.auth import dependencies as security_deps
    from app.shared.auth.principal import get_principal

    with override_dependencies({get_principal: security_deps.get_principal}):
        res = await async_client.post(
            f"/api/tasks/{task_id}/run",
            json={"branch": None, "workflowInputs": None},
            headers={"x-candidate-session-id": str(cs.id)},
        )
    assert res.status_code == 401
