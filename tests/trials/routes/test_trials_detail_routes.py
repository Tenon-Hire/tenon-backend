import pytest

from tests.shared.factories import create_talent_partner, create_trial


@pytest.mark.asyncio
async def test_get_trial_detail_happy_path(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="owner-detail@example.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    tasks[1].max_score = 42
    await async_session.commit()

    res = await async_client.get(
        f"/api/trials/{sim.id}", headers=auth_header_factory(talent_partner)
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["id"] == sim.id
    assert body["activeScenarioVersionId"] == sim.active_scenario_version_id
    assert body["pendingScenarioVersionId"] is None
    assert body["scenario"]["id"] == sim.active_scenario_version_id
    assert body["scenario"]["versionIndex"] == 1
    assert body["scenario"]["status"] in {"ready", "locked"}
    assert body["scenario"]["lockedAt"] is None
    assert body["scenario"]["notes"] == sim.focus
    assert body["templateKey"] == sim.template_key
    assert body["techStack"] == sim.tech_stack
    assert isinstance(body["tasks"], list)
    assert [task["dayIndex"] for task in body["tasks"]] == [
        task.day_index for task in tasks
    ]
    assert "dayIndex" in body["tasks"][0]
    assert "day_index" not in body["tasks"][0]
    assert "description" in body["tasks"][0]
    assert "rubric" in body["tasks"][0]
    assert body["tasks"][0]["rubric"] is None

    day2 = next(task for task in body["tasks"] if task["dayIndex"] == 2)
    assert "templateRepoFullName" in day2
    assert day2["templateRepoFullName"]
    assert day2["maxScore"] == 42
    day1 = next(task for task in body["tasks"] if task["dayIndex"] == 1)
    assert "templateRepoFullName" not in day1
    assert "preProvisioned" not in day1
    assert "maxScore" not in day1


@pytest.mark.asyncio
async def test_trial_context_round_trips_on_create_and_detail(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="context-detail@example.com"
    )
    payload = {
        "title": "Frontend Trial",
        "role": "Frontend Engineer",
        "techStack": "react-nextjs",
        "seniority": "mid",
        "focus": "Emphasize documentation and test discipline.",
        "companyContext": {"domain": "social", "productArea": "creator tools"},
        "ai": {
            "noticeVersion": "mvp1",
            "noticeText": "AI may assist with scenario generation.",
            "evalEnabledByDay": {
                "1": True,
                "2": True,
                "3": True,
                "4": False,
                "5": True,
            },
        },
    }

    create_res = await async_client.post(
        "/api/trials",
        json=payload,
        headers=auth_header_factory(talent_partner),
    )
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    assert created["seniority"] == "mid"
    assert created["focus"] == payload["focus"]
    assert created["companyContext"] == payload["companyContext"]
    assert created["ai"] == payload["ai"]

    detail_res = await async_client.get(
        f"/api/trials/{created['id']}",
        headers=auth_header_factory(talent_partner),
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["seniority"] == "mid"
    assert detail["focus"] == payload["focus"]
    assert detail["companyContext"] == payload["companyContext"]
    assert detail["ai"]["noticeVersion"] == payload["ai"]["noticeVersion"]
    assert detail["ai"]["noticeText"] == payload["ai"]["noticeText"]
    assert detail["ai"]["evalEnabledByDay"] == payload["ai"]["evalEnabledByDay"]
    assert detail["ai"]["promptPackVersion"] == "winoe-ai-pack-v1"
    assert detail["ai"]["changesPendingRegeneration"] is False
