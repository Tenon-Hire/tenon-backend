from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_rejects_completed(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="completed@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    cs, _created = await sim_service.create_invite(
        async_session,
        trial_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    cs.status = CANDIDATE_SESSION_STATUS_COMPLETED
    cs.completed_at = datetime.now(UTC)
    await async_session.commit()

    with pytest.raises(sim_service.InviteRejectedError) as excinfo:
        await sim_service.create_or_resend_invite(
            async_session, trial_id=sim.id, payload=payload, now=datetime.now(UTC)
        )
    assert excinfo.value.outcome == "rejected"
