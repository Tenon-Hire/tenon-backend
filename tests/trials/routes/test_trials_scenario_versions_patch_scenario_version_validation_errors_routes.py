from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_validation_errors(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-validation-api@test.com"
    )
    headers = auth_header_factory(talent_partner)
    sim_id = await _create_trial(async_client, async_session, headers)

    detail = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    scenario_version_id = detail.json()["activeScenarioVersionId"]
    assert scenario_version_id is not None

    malformed_shape = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"taskPrompts": {"dayIndex": 2, "description": "bad shape"}},
    )
    assert malformed_shape.status_code == 422, malformed_shape.text

    malformed_merged = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={
            "taskPrompts": [
                {"dayIndex": 2, "title": "A", "description": "A"},
                {"dayIndex": 2, "title": "B", "description": "B"},
            ]
        },
    )
    assert malformed_merged.status_code == 422, malformed_merged.text
    assert malformed_merged.json()["errorCode"] == "SCENARIO_PATCH_INVALID"

    oversized = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"storylineMd": "x" * (MAX_SCENARIO_STORYLINE_CHARS + 1)},
    )
    assert oversized.status_code == 422, oversized.text
    audits = (
        (
            await async_session.execute(
                select(ScenarioEditAudit).where(
                    ScenarioEditAudit.scenario_version_id == scenario_version_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
