from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_disallowed_status_returns_not_editable(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-disallowed-status-api@test.com"
    )
    headers = auth_header_factory(talent_partner)
    sim_id = await _create_trial(async_client, async_session, headers)

    detail = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    scenario_version_id = detail.json()["activeScenarioVersionId"]
    assert scenario_version_id is not None

    version = await async_session.get(ScenarioVersion, scenario_version_id)
    assert version is not None
    version.status = "draft"
    await async_session.commit()

    patch = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"notes": "Should fail for draft status"},
    )
    assert patch.status_code == 409, patch.text
    assert patch.json()["errorCode"] == "SCENARIO_NOT_EDITABLE"

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
