from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import HTTPException

from app.trials.services import (
    trials_services_trials_candidates_compare_service as compare_service,
)

derive_candidate_compare_status = compare_service.derive_candidate_compare_status
derive_winoe_report_status = compare_service.derive_winoe_report_status
list_candidates_compare_summary = compare_service.list_candidates_compare_summary
require_trial_compare_access = compare_service.require_trial_compare_access


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
        "winoe_report_generated_at": None,
        "latest_run_status": None,
        "latest_run_started_at": None,
        "latest_run_completed_at": None,
        "latest_run_generated_at": None,
        "latest_success_candidate_session_id": None,
        "overall_winoe_score": None,
        "recommendation": None,
        "latest_success_started_at": None,
        "latest_success_completed_at": None,
        "latest_success_generated_at": None,
        "active_job_updated_at": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


__all__ = [name for name in globals() if not name.startswith("__")]
