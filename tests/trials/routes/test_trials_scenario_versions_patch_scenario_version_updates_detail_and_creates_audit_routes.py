from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_updates_detail_and_creates_audit(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-api@test.com"
    )
    headers = auth_header_factory(talent_partner)
    sim_id = await _create_trial(async_client, async_session, headers)

    detail_before = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert detail_before.status_code == 200, detail_before.text
    before_body = detail_before.json()
    scenario_version_id = before_body["activeScenarioVersionId"]
    assert scenario_version_id is not None
    assert before_body["scenario"]["notes"] == "Scenario lock semantics"

    patch = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={
            "storylineMd": "## Updated storyline copy",
            "taskPrompts": [
                {
                    "dayIndex": 2,
                    "title": "Updated Day 2 Title",
                    "description": "Updated day 2 wording",
                }
            ],
            "rubric": {"dayWeights": {"2": 35}, "dimensions": []},
            "notes": "TalentPartner edited wording",
        },
    )
    assert patch.status_code == 200, patch.text
    patch_body = patch.json()
    assert patch_body == {
        "scenarioVersionId": scenario_version_id,
        "status": "ready",
    }

    detail_after = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert detail_after.status_code == 200, detail_after.text
    after_body = detail_after.json()
    assert after_body["scenario"]["storylineMd"] == "## Updated storyline copy"
    assert after_body["scenario"]["taskPromptsJson"] == [
        {
            "dayIndex": 2,
            "title": "Updated Day 2 Title",
            "description": "Updated day 2 wording",
        }
    ]
    assert after_body["scenario"]["rubricJson"] == {
        "dayWeights": {"2": 35},
        "dimensions": [],
    }
    assert after_body["scenario"]["notes"] == "TalentPartner edited wording"
    assert "focusNotes" not in after_body["scenario"]

    audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit)
                .where(ScenarioEditAudit.scenario_version_id == scenario_version_id)
                .order_by(ScenarioEditAudit.id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 1
    assert audits[0].talent_partner_id == talent_partner.id
    assert audits[0].patch_json == {
        "changedFields": [
            "storyline_md",
            "task_prompts_json",
            "rubric_json",
            "focus_notes",
        ],
        "before": {
            "storyline_md": before_body["scenario"]["storylineMd"],
            "task_prompts_json": before_body["scenario"]["taskPromptsJson"],
            "rubric_json": before_body["scenario"]["rubricJson"],
            "focus_notes": before_body["scenario"]["notes"],
        },
        "after": {
            "storyline_md": "## Updated storyline copy",
            "task_prompts_json": [
                {
                    "dayIndex": 2,
                    "title": "Updated Day 2 Title",
                    "description": "Updated day 2 wording",
                }
            ],
            "rubric_json": {
                "dayWeights": {"2": 35},
                "dimensions": [],
            },
            "focus_notes": "TalentPartner edited wording",
        },
    }
