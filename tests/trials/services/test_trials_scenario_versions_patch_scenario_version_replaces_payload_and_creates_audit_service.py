from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_replaces_payload_and_creates_audit(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    sim.status = "ready_for_review"
    await async_session.commit()

    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    assert isinstance(active.task_prompts_json, list)
    before_storyline = active.storyline_md
    before_task_prompts = list(active.task_prompts_json)
    before_rubric = dict(active.rubric_json)
    before_notes = active.focus_notes

    updated = await scenario_service.patch_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=talent_partner.id,
        updates={
            "storyline_md": "## Updated storyline",
            "task_prompts_json": [
                {
                    "dayIndex": 2,
                    "title": "Day 2 refreshed",
                    "description": "New day 2 wording",
                }
            ],
            "rubric_json": {"dayWeights": {"2": 35}},
            "focus_notes": "Updated notes",
        },
    )
    assert updated.storyline_md == "## Updated storyline"
    assert updated.focus_notes == "Updated notes"
    assert updated.task_prompts_json == [
        {"dayIndex": 2, "title": "Day 2 refreshed", "description": "New day 2 wording"}
    ]
    assert updated.rubric_json["dayWeights"]["2"] == 35

    audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit)
                .where(ScenarioEditAudit.scenario_version_id == active.id)
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
            "storyline_md": before_storyline,
            "task_prompts_json": before_task_prompts,
            "rubric_json": before_rubric,
            "focus_notes": before_notes,
        },
        "after": {
            "storyline_md": "## Updated storyline",
            "task_prompts_json": [
                {
                    "dayIndex": 2,
                    "title": "Day 2 refreshed",
                    "description": "New day 2 wording",
                }
            ],
            "rubric_json": {"dayWeights": {"2": 35}},
            "focus_notes": "Updated notes",
        },
    }
