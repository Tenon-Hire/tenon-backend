from __future__ import annotations

import pytest

from tests.candidates.candidate_sessions.services.candidates_candidate_sessions_day_close_jobs_test_utils import *


@pytest.mark.asyncio
async def test_enqueue_day_close_jobs_returns_empty_without_trial(async_session):
    candidate_session = SimpleNamespace(trial=None)
    jobs = await day_close_jobs.enqueue_day_close_finalize_text_jobs(
        async_session,
        candidate_session=candidate_session,
    )
    assert jobs == []
