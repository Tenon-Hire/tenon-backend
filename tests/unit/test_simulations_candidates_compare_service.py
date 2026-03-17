from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services.simulations import candidates_compare as compare_service
from app.services.simulations.candidates_compare import (
    derive_candidate_compare_status,
    derive_fit_profile_status,
    list_candidates_compare_summary,
    require_simulation_compare_access,
)


def _day_completion(*, completed_days: set[int] | None = None) -> dict[str, bool]:
    completed_days = completed_days or set()
    return {str(day): day in completed_days for day in range(1, 6)}


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, execute_results: list[object]):
        self._execute_results = list(execute_results)
        self.executed_statements = []

    async def execute(self, statement):
        self.executed_statements.append(statement)
        if not self._execute_results:
            raise AssertionError("unexpected execute call")
        return self._execute_results.pop(0)


def _candidate_row(**overrides):
    payload = {
        "candidate_session_id": 0,
        "candidate_name": "",
        "candidate_session_status": "not_started",
        "claimed_at": None,
        "started_at": None,
        "completed_at": None,
        "candidate_session_created_at": None,
        "candidate_session_updated_at": None,
        "schedule_locked_at": None,
        "invite_email_sent_at": None,
        "invite_email_last_attempt_at": None,
        "fit_profile_generated_at": None,
        "latest_run_status": None,
        "latest_run_started_at": None,
        "latest_run_completed_at": None,
        "latest_run_generated_at": None,
        "latest_success_candidate_session_id": None,
        "overall_fit_score": None,
        "recommendation": None,
        "latest_success_started_at": None,
        "latest_success_completed_at": None,
        "latest_success_generated_at": None,
        "active_job_updated_at": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


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
        compare_service._fit_profile_updated_at(
            _candidate_row(
                latest_run_completed_at=now,
                active_job_updated_at=later,
            )
        )
        == later
    )


def test_derive_candidate_compare_status_ready_is_evaluated():
    status = derive_candidate_compare_status(
        fit_profile_status="ready",
        day_completion=_day_completion(completed_days={1, 2}),
        candidate_session_status="in_progress",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    assert status == "evaluated"


def test_derive_candidate_compare_status_all_days_done_is_completed():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(completed_days={1, 2, 3, 4, 5}),
        candidate_session_status="in_progress",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    assert status == "completed"


def test_derive_candidate_compare_status_partial_progress_is_in_progress():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(completed_days={1}),
        candidate_session_status="not_started",
        started_at=None,
        completed_at=None,
    )
    assert status == "in_progress"


def test_derive_candidate_compare_status_no_progress_is_scheduled():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(),
        candidate_session_status="not_started",
        started_at=None,
        completed_at=None,
    )
    assert status == "scheduled"


def test_derive_candidate_compare_status_started_without_submissions_is_in_progress():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(),
        candidate_session_status="not_started",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    assert status == "in_progress"


def test_derive_fit_profile_status_prefers_ready():
    status = derive_fit_profile_status(
        has_ready_profile=True,
        latest_run_status="failed",
        has_active_job=True,
    )
    assert status == "ready"


def test_derive_fit_profile_status_pending_or_running_is_generating():
    pending = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status="pending",
        has_active_job=False,
    )
    running = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status="running",
        has_active_job=False,
    )
    assert pending == "generating"
    assert running == "generating"


def test_derive_fit_profile_status_failed_when_no_ready_or_active_job():
    status = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status="failed",
        has_active_job=False,
    )
    assert status == "failed"


def test_derive_fit_profile_status_active_job_without_runs_is_generating():
    status = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status=None,
        has_active_job=True,
    )
    assert status == "generating"


def test_derive_fit_profile_status_defaults_to_none():
    status = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status="unknown",
        has_active_job=False,
    )
    assert status == "none"


@pytest.mark.asyncio
async def test_require_simulation_compare_access_raises_404_when_not_found():
    db = _FakeDB([_ScalarResult(None)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_simulation_compare_access(db, simulation_id=77, user=user)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Simulation not found"


@pytest.mark.asyncio
async def test_require_simulation_compare_access_raises_403_for_company_scope():
    simulation = SimpleNamespace(id=77, company_id=8, created_by=100)
    db = _FakeDB([_ScalarResult(simulation)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_simulation_compare_access(db, simulation_id=77, user=user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Simulation access forbidden"


@pytest.mark.asyncio
async def test_require_simulation_compare_access_raises_403_for_non_owner():
    simulation = SimpleNamespace(id=77, company_id=5, created_by=101)
    db = _FakeDB([_ScalarResult(simulation)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_simulation_compare_access(db, simulation_id=77, user=user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Simulation access forbidden"


@pytest.mark.asyncio
async def test_require_simulation_compare_access_returns_context_for_owner():
    simulation = SimpleNamespace(id=77, company_id=5, created_by=100)
    db = _FakeDB([_ScalarResult(simulation)])
    user = SimpleNamespace(id=100, company_id=5)

    context = await require_simulation_compare_access(db, simulation_id=77, user=user)

    assert context.simulation_id == 77


@pytest.mark.asyncio
async def test_load_day_completion_returns_empty_dicts_for_no_candidates():
    completion, latest = await compare_service._load_day_completion(
        _FakeDB([]),
        simulation_id=77,
        candidate_session_ids=[],
    )

    assert completion == {}
    assert latest == {}


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
        simulation_id=77,
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
            overall_fit_score=0.82,
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
        "require_simulation_compare_access",
        AsyncMock(
            return_value=compare_service.SimulationCompareAccessContext(
                simulation_id=77
            )
        ),
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
        simulation_id=77,
        user=user,
    )
    after_call = datetime.now(UTC).replace(microsecond=0)

    assert "ORDER BY candidate_sessions.id ASC" in str(fake_db.executed_statements[0])
    assert payload["simulationId"] == 77
    assert [c["candidateSessionId"] for c in payload["candidates"]] == [
        101,
        102,
        103,
        104,
    ]

    first = payload["candidates"][0]
    assert first["candidateName"] == "Candidate A"
    assert first["candidateDisplayName"] == "Candidate A"
    assert first["status"] == "evaluated"
    assert first["fitProfileStatus"] == "ready"
    assert first["updatedAt"] == fit_timestamp

    second = payload["candidates"][1]
    assert second["candidateName"] == "Ada Lovelace"
    assert second["candidateDisplayName"] == "Ada Lovelace"
    assert second["status"] == "in_progress"
    assert second["fitProfileStatus"] == "generating"
    assert second["updatedAt"] == session_timestamp

    third = payload["candidates"][2]
    assert third["candidateName"] == "Candidate C"
    assert third["candidateDisplayName"] == "Candidate C"
    assert third["status"] == "scheduled"
    assert third["fitProfileStatus"] == "none"
    assert third["updatedAt"] == created_timestamp

    fourth = payload["candidates"][3]
    assert fourth["candidateName"] == "Candidate D"
    assert fourth["candidateDisplayName"] == "Candidate D"
    assert before_call <= fourth["updatedAt"] <= after_call
