import pytest

from tests.trials.routes.trials_update_api_utils import (
    create_trial,
    create_user,
)


@pytest.mark.asyncio
async def test_update_trial_rejects_invalid_ai_day_key(
    async_client, async_session, auth_header_factory
):
    talent_partner, _company = await create_user(
        async_session,
        company_name="InvalidAiUpdateCo",
        name="TalentPartner Invalid Update",
        email="talent_partner-invalid-update@acme.com",
    )
    trial_id = await create_trial(
        async_client,
        auth_header_factory,
        talent_partner,
        {
            "title": "Sim Invalid Update",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "Invalid AI update",
        },
    )
    update_res = await async_client.put(
        f"/api/trials/{trial_id}",
        headers=auth_header_factory(talent_partner),
        json={"ai": {"evalEnabledByDay": {"6": True}}},
    )
    assert update_res.status_code == 422, update_res.text
