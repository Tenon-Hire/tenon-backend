import pytest

from tests.simulations.routes.simulations_update_api_utils import (
    create_simulation,
    create_user,
)


@pytest.mark.asyncio
async def test_update_simulation_ai_partial_merge(
    async_client, async_session, auth_header_factory
):
    recruiter, _company = await create_user(
        async_session,
        company_name="UpdateCo",
        name="Recruiter Update",
        email="recruiter-update@acme.com",
    )
    simulation_id = await create_simulation(
        async_client,
        auth_header_factory,
        recruiter,
        {
            "title": "Sim Update",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Update AI controls",
            "ai": {
                "noticeVersion": "mvp1",
                "noticeText": "Initial notice text",
                "evalEnabledByDay": {
                    "1": True,
                    "2": True,
                    "3": True,
                    "4": False,
                    "5": True,
                },
            },
        },
    )
    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(recruiter),
        json={"ai": {"noticeVersion": "mvp2", "evalEnabledByDay": {"2": False}}},
    )
    assert update_res.status_code == 200, update_res.text
    body = update_res.json()
    assert body["id"] == simulation_id
    assert body["ai"]["noticeVersion"] == "mvp2"
    assert body["ai"]["noticeText"] == "Initial notice text"
    assert body["ai"]["evalEnabledByDay"] == {
        "1": True,
        "2": False,
        "3": True,
        "4": False,
        "5": True,
    }
