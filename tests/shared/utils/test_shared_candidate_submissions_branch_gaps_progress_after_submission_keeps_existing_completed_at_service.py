from __future__ import annotations

import pytest

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_progress_after_submission_keeps_existing_completed_at(monkeypatch):
    db = _DummyDB()
    completed_at = datetime(2025, 1, 1, tzinfo=UTC)
    candidate_session = SimpleNamespace(status="in_progress", completed_at=completed_at)

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
    assert candidate_session.status == "completed"
    assert candidate_session.completed_at == completed_at
    assert db.commits == 1
    assert db.refreshes == 1
