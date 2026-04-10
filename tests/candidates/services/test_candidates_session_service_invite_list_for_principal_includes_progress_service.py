from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_invite_list_for_principal_includes_progress(async_session):
    talent_partner = await create_talent_partner(async_session, email="list@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="jane@example.com",
        status="in_progress",
    )
    await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        content_text="day1",
    )
    await async_session.commit()

    principal = _principal(cs.invite_email)
    invites = await cs_service.invite_list_for_principal(async_session, principal)
    assert len(invites) == 1
    invite = invites[0]
    assert invite.candidateSessionId == cs.id
    assert invite.progress.completed == 1
    assert invite.progress.total == len(tasks)
