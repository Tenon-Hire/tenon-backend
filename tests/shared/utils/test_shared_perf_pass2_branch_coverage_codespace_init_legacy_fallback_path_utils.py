from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_codespace_init_legacy_fallback_path(monkeypatch):
    candidate_session = SimpleNamespace(id=1, trial_id=2)
    task = SimpleNamespace(id=5, trial_id=2, type="code")

    async def _raise_missing_tasks(*_args, **_kwargs):
        raise HTTPException(status_code=500, detail="Trial has no tasks")

    monkeypatch.setattr(
        codespace_init_use_case,
        "validate_codespace_request",
        _raise_missing_tasks,
    )
    monkeypatch.setattr(
        codespace_init_use_case.submission_service,
        "load_task_or_404",
        _async_return(task),
    )
    monkeypatch.setattr(
        codespace_init_use_case.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        codespace_init_use_case.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        codespace_init_use_case.cs_service,
        "progress_snapshot",
        _async_return(([], set(), task, 0, 1, False)),
    )
    monkeypatch.setattr(
        codespace_init_use_case.submission_service,
        "ensure_in_order",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        codespace_init_use_case.submission_service,
        "validate_run_allowed",
        lambda *_args, **_kwargs: None,
    )

    resolved = await _validate_codespace_request_with_legacy_fallback(
        object(), candidate_session, task.id
    )
    assert resolved is task
