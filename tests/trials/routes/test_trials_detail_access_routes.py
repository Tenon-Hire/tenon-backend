import pytest

from tests.shared.factories import create_talent_partner, create_trial


@pytest.mark.asyncio
async def test_get_trial_detail_not_found(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="missing-detail@example.com"
    )
    await async_session.commit()

    res = await async_client.get(
        "/api/trials/999999", headers=auth_header_factory(talent_partner)
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_trial_detail_unauthorized(async_client):
    res = await async_client.get("/api/trials/1")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_trial_detail_rejects_unowned(
    async_client, async_session, auth_header_factory
):
    owner = await create_talent_partner(async_session, email="owner-sim@example.com")
    outsider = await create_talent_partner(
        async_session, email="outsider-sim@example.com"
    )
    sim, _ = await create_trial(async_session, created_by=owner)
    await async_session.commit()

    res = await async_client.get(
        f"/api/trials/{sim.id}", headers=auth_header_factory(outsider)
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_trial_detail_forbidden_for_non_talent_partner(
    async_client, async_session
):
    candidate_user = await create_talent_partner(
        async_session, email="candidate-detail@example.com", company_name="CandCo"
    )
    candidate_user.role = "candidate"
    await async_session.commit()

    res = await async_client.get(
        "/api/trials/1", headers={"x-dev-user-email": candidate_user.email}
    )
    assert res.status_code == 403
