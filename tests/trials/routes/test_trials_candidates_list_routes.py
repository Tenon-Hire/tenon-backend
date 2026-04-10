import pytest

from tests.trials.routes.trials_candidates_api_utils import (
    create_trial,
    seed_talent_partner,
)


@pytest.mark.asyncio
async def test_trial_with_no_candidate_sessions_returns_empty_list(
    async_client, async_session
):
    user, company = await seed_talent_partner(
        async_session,
        email="r1@acme.com",
        company_name="Acme",
        name="TalentPartner One",
    )
    sim = await create_trial(
        async_session, user_id=user.id, company_id=company.id, title="Test Sim"
    )
    await async_session.commit()
    resp = await async_client.get(
        f"/api/trials/{sim.id}/candidates",
        headers={"x-dev-user-email": user.email},
    )
    assert resp.status_code == 200
    assert resp.json() == []
