from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_progress_after_submission_skips_commit_for_already_completed(
    monkeypatch,
):
    db = _DummyDB()
    candidate_session = SimpleNamespace(
        status="completed", completed_at=datetime.now(UTC)
    )

    async def _snapshot(_db, _candidate_session):
        return (
            None,
            {1, 2, 3, 4, 5},
            None,
            5,
            5,
            True,
        )

    monkeypatch.setattr(submission_progress.cs_service, "progress_snapshot", _snapshot)

    completed, total, is_complete = await submission_progress.progress_after_submission(
        db,
        candidate_session,
        now=datetime.now(UTC),
    )

    assert (completed, total, is_complete) == (5, 5, True)
    assert db.commits == 0
    assert db.refreshes == 0
