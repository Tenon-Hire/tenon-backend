import pytest

from tests.trials.routes.trials_update_api_utils import (
    create_trial,
    create_user,
)


@pytest.mark.asyncio
async def test_update_trial_omitted_ai_preserves_existing(
    async_client, async_session, auth_header_factory
):
    talent_partner, _company = await create_user(
        async_session,
        company_name="PreserveCo",
        name="TalentPartner Preserve",
        email="talent_partner-preserve@acme.com",
    )
    trial_id = await create_trial(
        async_client,
        auth_header_factory,
        talent_partner,
        {
            "title": "Sim Preserve",
            "role": "Backend Engineer",
            "techStack": "Python",
            "seniority": "Mid",
            "focus": "No-op AI update",
            "ai": {
                "noticeVersion": "mvp9",
                "noticeText": "Custom notice",
                "evalEnabledByDay": {
                    "1": True,
                    "2": False,
                    "3": True,
                    "4": True,
                    "5": False,
                },
            },
        },
    )
    update_res = await async_client.put(
        f"/api/trials/{trial_id}",
        headers=auth_header_factory(talent_partner),
        json={},
    )
    assert update_res.status_code == 200, update_res.text
    body = update_res.json()
    assert body["ai"]["noticeVersion"] == "mvp9"
    assert body["ai"]["noticeText"] == "Custom notice"
    assert body["ai"]["evalEnabledByDay"] == {
        "1": True,
        "2": False,
        "3": True,
        "4": True,
        "5": False,
    }
    assert body["ai"]["changesPendingRegeneration"] is False
