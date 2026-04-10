import pytest

from tests.trials.routes.trials_update_api_utils import (
    create_trial,
    create_user,
)


@pytest.mark.asyncio
async def test_update_trial_ai_partial_merge(
    async_client, async_session, auth_header_factory
):
    talent_partner, _company = await create_user(
        async_session,
        company_name="UpdateCo",
        name="TalentPartner Update",
        email="talent_partner-update@acme.com",
    )
    trial_id = await create_trial(
        async_client,
        auth_header_factory,
        talent_partner,
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
        f"/api/trials/{trial_id}",
        headers=auth_header_factory(talent_partner),
        json={"ai": {"noticeVersion": "mvp2", "evalEnabledByDay": {"2": False}}},
    )
    assert update_res.status_code == 200, update_res.text
    body = update_res.json()
    assert body["id"] == trial_id
    assert body["ai"]["noticeVersion"] == "mvp2"
    assert body["ai"]["noticeText"] == "Initial notice text"
    assert body["ai"]["evalEnabledByDay"] == {
        "1": True,
        "2": False,
        "3": True,
        "4": False,
        "5": True,
    }
