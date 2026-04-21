from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_talent_partner_cannot_read_another_talent_partners_candidates(
    async_client, async_session, override_dependencies
):
    await create_talent_partner(async_session, email="owner-a@test.com")
    owner_b = await create_talent_partner(async_session, email="owner-b@test.com")
    trial_b, _ = await create_trial(async_session, created_by=owner_b)
    await create_candidate_session(async_session, trial=trial_b)

    from app.shared.auth import dependencies as security_deps
    from app.shared.auth.dependencies import get_current_user

    with override_dependencies({get_current_user: security_deps.get_current_user}):
        response = await async_client.get(
            f"/api/trials/{trial_b.id}/candidates",
            headers={"Authorization": "Bearer talent_partner:owner-a@test.com"},
        )

    # The app hides cross-tenant trial existence by returning its real 404 denial.
    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Trial not found"}
