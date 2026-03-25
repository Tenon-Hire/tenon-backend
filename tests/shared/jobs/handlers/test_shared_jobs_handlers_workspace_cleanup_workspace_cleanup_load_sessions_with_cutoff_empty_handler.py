from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_load_sessions_with_cutoff_empty(async_session):
    session_ids = await cleanup_handler._load_sessions_with_cutoff(
        async_session,
        candidate_session_ids=[],
    )
    assert session_ids == set()
