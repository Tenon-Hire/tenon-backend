from __future__ import annotations

import pytest

from tests.trials.services.trials_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_load_day_completion_tracks_completed_days_and_latest_submission():
    older = datetime(2026, 3, 16, 8, 0, tzinfo=UTC)
    newer = datetime(2026, 3, 16, 9, 0, tzinfo=UTC)
    rows = [
        SimpleNamespace(
            candidate_session_id=9,
            day_index=6,
            task_count=1,
            submitted_count=1,
            latest_submission_at=older,
        ),
        SimpleNamespace(
            candidate_session_id=9,
            day_index=1,
            task_count=2,
            submitted_count=2,
            latest_submission_at=older,
        ),
        SimpleNamespace(
            candidate_session_id=9,
            day_index=2,
            task_count=2,
            submitted_count=1,
            latest_submission_at=None,
        ),
        SimpleNamespace(
            candidate_session_id=9,
            day_index=3,
            task_count=1,
            submitted_count=1,
            latest_submission_at=newer,
        ),
    ]

    completion, latest = await compare_service._load_day_completion(
        _FakeDB([_RowsResult(rows)]),
        trial_id=77,
        candidate_session_ids=[9],
    )

    assert completion[9] == {
        "1": True,
        "2": False,
        "3": True,
        "4": False,
        "5": False,
    }
    assert latest[9] == newer
