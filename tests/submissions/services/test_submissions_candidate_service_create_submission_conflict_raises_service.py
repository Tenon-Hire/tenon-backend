from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_create_submission_conflict_raises(async_session):
    talent_partner = await create_talent_partner(async_session, email="dup@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    payload = SimpleNamespace(contentText="text")
    # seed one submission
    await svc.create_submission(
        async_session,
        cs,
        tasks[0],
        payload,
        now=datetime.now(UTC),
    )

    with pytest.raises(HTTPException) as excinfo:
        await svc.create_submission(
            async_session,
            cs,
            tasks[0],
            payload,
            now=datetime.now(UTC),
        )
    assert excinfo.value.status_code == 409
