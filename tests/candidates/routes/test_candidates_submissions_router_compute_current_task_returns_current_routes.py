from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_compute_current_task_returns_current(monkeypatch, async_session):
    cs = _stub_cs()
    current = _stub_task()

    async def _fake_snapshot(db, _cs):
        return ([], set(), current, 0, 1, False)

    monkeypatch.setattr(
        candidate_submissions.cs_service, "progress_snapshot", _fake_snapshot
    )
    assert (
        await candidate_submissions._compute_current_task(async_session, cs) is current
    )
