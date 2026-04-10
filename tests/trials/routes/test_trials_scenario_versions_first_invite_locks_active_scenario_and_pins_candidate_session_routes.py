from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_first_invite_locks_active_scenario_and_pins_candidate_session(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-lock@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(talent_partner)
    )

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    detail_before = await async_client.get(
        f"/api/trials/{sim_id}", headers=auth_header_factory(talent_partner)
    )
    assert detail_before.status_code == 200, detail_before.text
    scenario_before = detail_before.json()["scenario"]
    assert scenario_before["versionIndex"] == 1
    assert scenario_before["status"] == "ready"
    assert scenario_before["lockedAt"] is None

    invite = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane-lock@example.com"},
    )
    assert invite.status_code == 200, invite.text
    body = invite.json()

    detail_after = await async_client.get(
        f"/api/trials/{sim_id}", headers=auth_header_factory(talent_partner)
    )
    assert detail_after.status_code == 200, detail_after.text
    scenario_after = detail_after.json()["scenario"]
    assert scenario_after["id"] == scenario_before["id"]
    assert scenario_after["status"] == "locked"
    assert scenario_after["lockedAt"] is not None

    candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(
                CandidateSession.id == body["candidateSessionId"]
            )
        )
    ).scalar_one()
    assert candidate_session.scenario_version_id == scenario_before["id"]
