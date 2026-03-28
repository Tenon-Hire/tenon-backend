from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    SubmissionConflict,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_submit_validation_service as submit_validation,
)


@pytest.mark.asyncio
async def test_validate_submission_flow_raises_conflict_for_completed_task(monkeypatch):
    candidate_session = SimpleNamespace(id=7)
    task = SimpleNamespace(id=3)
    payload = SimpleNamespace(contentText="hello")

    async def _load_task(_db, task_id):
        assert task_id == task.id
        return task

    async def _progress_snapshot(_db, _candidate_session):
        return [task], [task.id], task, 1, False

    monkeypatch.setattr(
        submit_validation.submission_service, "load_task_or_404", _load_task
    )
    monkeypatch.setattr(
        submit_validation.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        submit_validation.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        submit_validation.cs_service, "progress_snapshot", _progress_snapshot
    )

    with pytest.raises(SubmissionConflict):
        await submit_validation.validate_submission_flow(
            db=object(),
            candidate_session=candidate_session,
            task_id=task.id,
            payload=payload,
        )
