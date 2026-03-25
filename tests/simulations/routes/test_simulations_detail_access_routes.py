import pytest

from tests.shared.factories import create_recruiter, create_simulation


@pytest.mark.asyncio
async def test_get_simulation_detail_not_found(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="missing-detail@example.com"
    )
    await async_session.commit()

    res = await async_client.get(
        "/api/simulations/999999", headers=auth_header_factory(recruiter)
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_simulation_detail_unauthorized(async_client):
    res = await async_client.get("/api/simulations/1")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_simulation_detail_rejects_unowned(
    async_client, async_session, auth_header_factory
):
    owner = await create_recruiter(async_session, email="owner-sim@example.com")
    outsider = await create_recruiter(async_session, email="outsider-sim@example.com")
    sim, _ = await create_simulation(async_session, created_by=owner)
    await async_session.commit()

    res = await async_client.get(
        f"/api/simulations/{sim.id}", headers=auth_header_factory(outsider)
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_simulation_detail_forbidden_for_non_recruiter(
    async_client, async_session
):
    candidate_user = await create_recruiter(
        async_session, email="candidate-detail@example.com", company_name="CandCo"
    )
    candidate_user.role = "candidate"
    await async_session.commit()

    res = await async_client.get(
        "/api/simulations/1", headers={"x-dev-user-email": candidate_user.email}
    )
    assert res.status_code == 403
