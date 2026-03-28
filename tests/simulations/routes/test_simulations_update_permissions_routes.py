import pytest

from app.simulations.constants.simulations_constants_simulations_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
)
from tests.simulations.routes.simulations_update_api_utils import (
    create_simulation,
    create_user,
)


@pytest.mark.asyncio
async def test_update_simulation_forbidden_for_non_recruiter(
    async_client, async_session, auth_header_factory
):
    recruiter, company = await create_user(
        async_session,
        company_name="ForbiddenCo",
        name="Recruiter Owner",
        email="recruiter-owner@acme.com",
    )
    candidate, _ = await create_user(
        async_session,
        company_name=None,
        name="Candidate User",
        email="candidate-user@acme.com",
        role="candidate",
        company_id=company.id,
    )
    simulation_id = await create_simulation(
        async_client,
        auth_header_factory,
        recruiter,
        {
            "title": "Sim Forbidden",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Forbidden updates",
        },
    )
    update_res = await async_client.put(
        f"/api/simulations/{simulation_id}",
        headers=auth_header_factory(candidate),
        json={
            "ai": {
                "noticeVersion": "mvp2",
                "noticeText": AI_NOTICE_DEFAULT_TEXT,
                "evalEnabledByDay": {"1": False},
            }
        },
    )
    assert update_res.status_code == 403, update_res.text
