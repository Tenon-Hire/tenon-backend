from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

from app.services.candidate_sessions import progress as progress_service


@dataclass
class _TaskStub:
    id: int
    day_index: int
    type: str


def test_handoff_revisit_task_returns_prior_handoff_when_next_window_start_missing(
    monkeypatch,
):
    handoff_task = _TaskStub(id=4, day_index=4, type="handoff")
    day5_task = _TaskStub(id=5, day_index=5, type="documentation")

    monkeypatch.setattr(
        progress_service,
        "compute_task_window",
        lambda *_args, **_kwargs: SimpleNamespace(window_start_at=None),
    )

    current = progress_service._handoff_revisit_task(
        [handoff_task, day5_task],
        {handoff_task.id},
        day5_task,
        candidate_session=SimpleNamespace(id=1),
        now_utc=datetime.now(UTC),
    )

    assert current is handoff_task
