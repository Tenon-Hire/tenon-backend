import pytest

from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_NOTICE_DEFAULT_TEXT,
)
from tests.trials.routes.trials_update_api_utils import (
    create_trial,
    create_user,
)


@pytest.mark.asyncio
async def test_update_trial_forbidden_for_non_talent_partner(
    async_client, async_session, auth_header_factory
):
    talent_partner, company = await create_user(
        async_session,
        company_name="ForbiddenCo",
        name="TalentPartner Owner",
        email="talent_partner-owner@acme.com",
    )
    candidate, _ = await create_user(
        async_session,
        company_name=None,
        name="Candidate User",
        email="candidate-user@acme.com",
        role="candidate",
        company_id=company.id,
    )
    trial_id = await create_trial(
        async_client,
        auth_header_factory,
        talent_partner,
        {
            "title": "Sim Forbidden",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Forbidden updates",
        },
    )
    update_res = await async_client.put(
        f"/api/trials/{trial_id}",
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
