import pytest

from tests.simulations.routes.simulations_update_api_utils import (
    create_simulation,
    create_user,
)


@pytest.mark.asyncio
async def test_update_simulation_rejects_invalid_ai_day_key(
    async_client, async_session, auth_header_factory
):
    recruiter, _company = await create_user(
        async_session,
        company_name="InvalidAiUpdateCo",
        name="Recruiter Invalid Update",
        email="recruiter-invalid-update@acme.com",
    )
    simulation_id = await create_simulation(
        async_client,
        auth_header_factory,
        recruiter,
        {
            "title": "Sim Invalid Update",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Invalid AI update",
        },
    )
    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(recruiter),
        json={"ai": {"evalEnabledByDay": {"6": True}}},
    )
    assert update_res.status_code == 422, update_res.text
