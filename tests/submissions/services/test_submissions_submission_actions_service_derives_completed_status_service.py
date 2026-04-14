from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.github.actions_runner import ActionsRunResult
from app.submissions.services.submissions_services_submissions_submission_actions_service import (
    derive_actions_metadata,
)


def test_derive_actions_metadata_persists_workflow_completion_fields():
    now = datetime(2026, 4, 2, 15, 30, tzinfo=UTC)

    result = ActionsRunResult(
        status="passed",
        run_id=12345,
        conclusion="SUCCESS",
        passed=8,
        failed=0,
        total=8,
        stdout="ok",
        stderr=None,
        head_sha="abc123",
        html_url="https://github.example/run/12345",
    )

    metadata = derive_actions_metadata(result, now)

    assert metadata["workflow_run_id"] == "12345"
    assert metadata["workflow_run_status"] == "completed"
    assert metadata["workflow_run_conclusion"] == "success"
    assert metadata["workflow_run_completed_at"] == now
    assert metadata["last_run_at"] == now
    assert metadata["commit_sha"] == "abc123"


def test_derive_actions_metadata_returns_defaults_when_missing():
    now = datetime(2026, 4, 2, 15, 30, tzinfo=UTC)

    metadata = derive_actions_metadata(None, now)

    assert metadata == {
        "tests_passed": None,
        "tests_failed": None,
        "test_output": None,
        "commit_sha": None,
        "workflow_run_id": None,
        "workflow_run_status": None,
        "workflow_run_conclusion": None,
        "workflow_run_completed_at": None,
        "last_run_at": None,
    }


def test_derive_actions_metadata_marks_running_workflow_in_progress():
    now = datetime(2026, 4, 2, 15, 30, tzinfo=UTC)

    result = ActionsRunResult(
        status="running",
        run_id=12346,
        conclusion="",
        passed=0,
        failed=0,
        total=0,
        stdout="",
        stderr=None,
        head_sha="def456",
        html_url="https://github.example/run/12346",
    )

    metadata = derive_actions_metadata(result, now)

    assert metadata["workflow_run_status"] == "in_progress"
    assert metadata["workflow_run_completed_at"] is None
