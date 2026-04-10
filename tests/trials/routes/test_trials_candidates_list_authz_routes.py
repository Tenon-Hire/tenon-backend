import pytest

from tests.trials.routes.trials_candidates_api_utils import (
    create_trial,
    seed_talent_partner,
)


@pytest.mark.asyncio
async def test_talent_partner_who_does_not_own_trial_gets_404(
    async_client, async_session
):
    owner, owner_company = await seed_talent_partner(
        async_session, email="owner@acme.com", company_name="AcmeOwner", name="Owner"
    )
    other, _ = await seed_talent_partner(
        async_session,
        email="other@beta.com",
        company_name="Beta",
        name="Other TalentPartner",
    )
    sim = await create_trial(
        async_session,
        user_id=owner.id,
        company_id=owner_company.id,
        title="Private Sim",
    )
    await async_session.commit()
    resp = await async_client.get(
        f"/api/trials/{sim.id}/candidates",
        headers={"x-dev-user-email": other.email},
    )
    assert resp.status_code == 404
