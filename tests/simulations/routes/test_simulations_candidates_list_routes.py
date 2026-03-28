import pytest

from tests.simulations.routes.simulations_candidates_api_utils import (
    create_simulation,
    seed_recruiter,
)


@pytest.mark.asyncio
async def test_simulation_with_no_candidate_sessions_returns_empty_list(
    async_client, async_session
):
    user, company = await seed_recruiter(
        async_session, email="r1@acme.com", company_name="Acme", name="Recruiter One"
    )
    sim = await create_simulation(
        async_session, user_id=user.id, company_id=company.id, title="Test Sim"
    )
    await async_session.commit()
    resp = await async_client.get(
        f"/api/simulations/{sim.id}/candidates",
        headers={"x-dev-user-email": user.email},
    )
    assert resp.status_code == 200
    assert resp.json() == []
