from __future__ import annotations

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


def test_mark_in_progress_preserves_existing_started_at():
    existing_started_at = datetime(2026, 1, 1, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        status="not_started", started_at=existing_started_at
    )

    status_service.mark_in_progress(candidate_session, now=datetime.now(UTC))

    assert candidate_session.status == "in_progress"
    assert candidate_session.started_at == existing_started_at
