from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_invites_api_utils import *


@pytest.mark.asyncio
async def test_invite_not_owned_simulation_returns_404(
    async_client, async_session: AsyncSession
):
    await seed_recruiter(
        async_session,
        email="recruiterA@tenon.com",
        company_name="Recruiter A Co",
    )
    await seed_recruiter(
        async_session,
        email="recruiterB@tenon.com",
        company_name="Recruiter B Co",
    )

    sim_id = await _create_and_activate_simulation(
        async_client, async_session, "recruiterA@tenon.com"
    )

    # Recruiter B attempts invite -> 404 (do not leak existence)
    resp = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers={"x-dev-user-email": "recruiterB@tenon.com"},
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert resp.status_code == 404
