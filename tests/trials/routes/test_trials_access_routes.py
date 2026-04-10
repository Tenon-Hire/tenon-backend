import pytest

from tests.shared.factories import create_talent_partner


@pytest.mark.asyncio
async def test_create_trial_forbidden_for_non_talent_partner(
    async_client, async_session
):
    candidate_user = await create_talent_partner(
        async_session, email="candidate@sim.com", name="Cand", company_name="Cand Co"
    )
    # flip role to candidate to exercise 403 path
    candidate_user.role = "candidate"
    await async_session.commit()

    res = await async_client.post(
        "/api/trials",
        headers={"x-dev-user-email": candidate_user.email},
        json={
            "title": "Should Fail",
            "role": "Backend",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "N/A",
        },
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_trials_forbidden_for_non_talent_partner(
    async_client, async_session
):
    candidate_user = await create_talent_partner(
        async_session, email="candidate2@sim.com", name="Cand2", company_name="Cand2 Co"
    )
    candidate_user.role = "candidate"
    await async_session.commit()

    res = await async_client.get(
        "/api/trials", headers={"x-dev-user-email": candidate_user.email}
    )
    assert res.status_code == 403
