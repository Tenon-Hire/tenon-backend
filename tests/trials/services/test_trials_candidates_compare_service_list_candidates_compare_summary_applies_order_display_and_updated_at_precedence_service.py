from __future__ import annotations

import pytest

from tests.trials.services.trials_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_list_candidates_compare_summary_applies_order_display_and_updated_at_precedence(
    monkeypatch,
):
    fit_timestamp = datetime(2026, 3, 16, 10, 15, tzinfo=UTC)
    session_timestamp = datetime(2026, 3, 16, 9, 45, tzinfo=UTC)
    created_timestamp = datetime(2026, 3, 16, 8, 30, tzinfo=UTC)

    rows = [
        _candidate_row(
            candidate_session_id=101,
            candidate_name="   ",
            candidate_session_status="completed",
            candidate_session_updated_at=fit_timestamp + timedelta(hours=1),
            latest_run_status="completed",
            latest_success_candidate_session_id=101,
            overall_winoe_score=0.82,
            recommendation="hire",
            latest_success_completed_at=fit_timestamp,
        ),
        _candidate_row(
            candidate_session_id=102,
            candidate_name="Ada Lovelace",
            latest_run_status="running",
        ),
        _candidate_row(
            candidate_session_id=103,
            candidate_name="",
            candidate_session_created_at=created_timestamp,
        ),
        _candidate_row(
            candidate_session_id=104,
            candidate_name="   ",
        ),
    ]
    fake_db = _FakeDB([_RowsResult(rows)])
    user = SimpleNamespace(id=700, company_id=55)
    before_call = datetime.now(UTC).replace(microsecond=0)

    monkeypatch.setattr(
        compare_service,
        "require_trial_compare_access",
        AsyncMock(return_value=compare_service.TrialCompareAccessContext(trial_id=77)),
    )
    monkeypatch.setattr(
        compare_service,
        "_load_day_completion",
        AsyncMock(
            return_value=(
                {
                    101: _day_completion(completed_days={1, 2, 3, 4, 5}),
                    102: _day_completion(completed_days={1}),
                    103: _day_completion(),
                    104: _day_completion(),
                },
                {
                    101: None,
                    102: session_timestamp,
                    103: None,
                    104: None,
                },
            )
        ),
    )

    payload = await list_candidates_compare_summary(
        fake_db,
        trial_id=77,
        user=user,
    )
    after_call = datetime.now(UTC).replace(microsecond=0)

    assert "ORDER BY candidate_sessions.id ASC" in str(fake_db.executed_statements[0])
    assert payload["trialId"] == 77
    assert [c["candidateSessionId"] for c in payload["candidates"]] == [
        101,
        102,
        103,
        104,
    ]
    expected = [
        ("Candidate A", "evaluated", "ready", fit_timestamp),
        ("Ada Lovelace", "in_progress", "generating", session_timestamp),
        ("Candidate C", "scheduled", "none", created_timestamp),
    ]
    for candidate, (name, status_value, winoe_report_status, updated_at) in zip(
        payload["candidates"][:3],
        expected,
        strict=True,
    ):
        assert candidate["candidateName"] == name
        assert candidate["candidateDisplayName"] == name
        assert candidate["status"] == status_value
        assert candidate["winoeReportStatus"] == winoe_report_status
        assert candidate["updatedAt"] == updated_at

    fourth = payload["candidates"][3]
    assert fourth["candidateName"] == "Candidate D"
    assert fourth["candidateDisplayName"] == "Candidate D"
    assert before_call <= fourth["updatedAt"] <= after_call
