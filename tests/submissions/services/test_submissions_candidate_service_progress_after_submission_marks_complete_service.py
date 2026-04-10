from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_progress_after_submission_marks_complete(async_session):
    talent_partner = await create_talent_partner(async_session, email="done@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
    )
    now = datetime.now(UTC)
    for task in tasks:
        await svc.create_submission(
            async_session, cs, task, SimpleNamespace(contentText="x"), now=now
        )

    completed, total, is_complete = await svc.progress_after_submission(
        async_session, cs, now=now
    )
    assert is_complete is True
    assert completed == total == 5
    await async_session.refresh(cs)
    assert cs.status == "completed"
