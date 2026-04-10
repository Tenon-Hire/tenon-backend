from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_codespace_validation_falls_back_to_task_lookup(monkeypatch):
    candidate_session = SimpleNamespace(id=7, trial_id=9)
    task = SimpleNamespace(id=11, trial_id=9, type="code")
    called = {"belongs": False}

    async def _snapshot(*_args, **_kwargs):
        return ([], set(), None, 0, 0, False)

    monkeypatch.setattr(
        codespace_validations.cs_service, "progress_snapshot", _snapshot
    )
    monkeypatch.setattr(
        codespace_validations.submission_service,
        "load_task_or_404",
        _async_return(task),
    )
    monkeypatch.setattr(
        codespace_validations.submission_service,
        "ensure_task_belongs",
        lambda *_args, **_kwargs: called.__setitem__("belongs", True),
    )
    monkeypatch.setattr(
        codespace_validations.cs_service,
        "require_active_window",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        codespace_validations.submission_service,
        "ensure_in_order",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        codespace_validations.submission_service,
        "validate_run_allowed",
        lambda *_args, **_kwargs: None,
    )

    resolved = await codespace_validations.validate_codespace_request(
        object(), candidate_session, task.id
    )
    assert resolved is task
    assert called["belongs"] is True
