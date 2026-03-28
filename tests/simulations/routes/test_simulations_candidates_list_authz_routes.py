import pytest

from tests.simulations.routes.simulations_candidates_api_utils import (
    create_simulation,
    seed_recruiter,
)


@pytest.mark.asyncio
async def test_recruiter_who_does_not_own_simulation_gets_404(
    async_client, async_session
):
    owner, owner_company = await seed_recruiter(
        async_session, email="owner@acme.com", company_name="AcmeOwner", name="Owner"
    )
    other, _ = await seed_recruiter(
        async_session,
        email="other@beta.com",
        company_name="Beta",
        name="Other Recruiter",
    )
    sim = await create_simulation(
        async_session,
        user_id=owner.id,
        company_id=owner_company.id,
        title="Private Sim",
    )
    await async_session.commit()
    resp = await async_client.get(
        f"/api/simulations/{sim.id}/candidates",
        headers={"x-dev-user-email": other.email},
    )
    assert resp.status_code == 404
