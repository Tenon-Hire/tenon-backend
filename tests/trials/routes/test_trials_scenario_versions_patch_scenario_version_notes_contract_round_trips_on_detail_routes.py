from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_notes_contract_round_trips_on_detail(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-notes-contract@test.com"
    )
    headers = auth_header_factory(talent_partner)
    sim_id = await _create_trial(async_client, async_session, headers)

    before_detail = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert before_detail.status_code == 200, before_detail.text
    scenario_version_id = before_detail.json()["activeScenarioVersionId"]
    assert scenario_version_id is not None

    patch = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"notes": "Only notes were edited"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["scenarioVersionId"] == scenario_version_id

    after_detail = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert after_detail.status_code == 200, after_detail.text
    scenario_payload = after_detail.json()["scenario"]
    assert scenario_payload["notes"] == "Only notes were edited"
    assert "focusNotes" not in scenario_payload
    assert "focus_notes" not in scenario_payload
