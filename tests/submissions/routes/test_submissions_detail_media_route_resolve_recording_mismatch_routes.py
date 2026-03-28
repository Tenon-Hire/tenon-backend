from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.submissions.routes.submissions_detail_media_routes_utils import detail_route


@pytest.mark.asyncio
async def test_resolve_recording_returns_none_for_mismatched_session_or_task(
    monkeypatch,
):
    mismatched_recording = SimpleNamespace(
        candidate_session_id=999,
        task_id=888,
    )

    async def _get_by_id(_db, _recording_id):
        return mismatched_recording

    async def _get_latest_for_task_session(*_args, **_kwargs):
        raise AssertionError(
            "latest lookup should not run when submission recording id is present"
        )

    monkeypatch.setattr(detail_route.recordings_repo, "get_by_id", _get_by_id)
    monkeypatch.setattr(
        detail_route.recordings_repo,
        "get_latest_for_task_session",
        _get_latest_for_task_session,
    )

    resolved = await detail_route._resolve_recording(
        object(),
        sub=SimpleNamespace(recording_id=123, candidate_session_id=1, task_id=2),
        task=SimpleNamespace(id=2),
        cs=SimpleNamespace(id=1),
    )

    assert resolved is None
