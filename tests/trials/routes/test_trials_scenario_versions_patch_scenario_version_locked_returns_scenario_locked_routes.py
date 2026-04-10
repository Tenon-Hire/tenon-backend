from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_locked_returns_scenario_locked(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-locked-api@test.com"
    )
    headers = auth_header_factory(talent_partner)
    sim_id = await _create_trial(async_client, async_session, headers)

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=headers,
        json={"candidateName": "Lock Me", "inviteEmail": "lockme@example.com"},
    )
    assert invite.status_code == 200, invite.text

    detail = await async_client.get(f"/api/trials/{sim_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    scenario_version_id = detail.json()["activeScenarioVersionId"]
    assert scenario_version_id is not None

    patch = await async_client.patch(
        f"/api/trials/{sim_id}/scenario/{scenario_version_id}",
        headers=headers,
        json={"notes": "Should fail"},
    )
    assert patch.status_code == 409, patch.text
    assert patch.json() == {
        "detail": "Scenario version is locked.",
        "errorCode": "SCENARIO_LOCKED",
    }
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
