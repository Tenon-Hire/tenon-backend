from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_compare_helpers_cover_edge_branches():
    now = datetime(2026, 3, 16, 10, 0, tzinfo=UTC)
    later = now + timedelta(minutes=1)

    assert compare_service._max_datetime() is None
    assert compare_service._anonymized_candidate_label(-3) == "Candidate A"
    assert compare_service._anonymized_candidate_label(27) == "Candidate AB"
    assert compare_service._normalize_score(True) is None
    assert compare_service._normalize_score(1.2) is None
    assert compare_service._normalize_recommendation(" maybe ") is None
    assert (
        compare_service._candidate_session_created_at(
            SimpleNamespace(candidate_session_created_at="not-a-datetime")
        )
        is None
    )
    assert (
        compare_service._winoe_report_updated_at(
            _candidate_row(
                latest_run_completed_at=now,
                active_job_updated_at=later,
            )
        )
        == later
    )
