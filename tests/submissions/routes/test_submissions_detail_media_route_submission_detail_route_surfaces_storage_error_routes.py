from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_detail_media_routes_utils import *


@pytest.mark.asyncio
async def test_submission_detail_route_surfaces_storage_error(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="detail-route-error@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff notes",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/error.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    class _BrokenProvider:
        def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
            del key, expires_seconds
            raise StorageMediaError("storage unavailable")

    monkeypatch.setattr(detail_route, "get_storage_media_provider", _BrokenProvider)

    with pytest.raises(HTTPException) as exc_info:
        await detail_route.get_submission_detail_route(
            submission_id=submission.id,
            db=async_session,
            user=talent_partner,
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Media storage unavailable"
    assert getattr(exc_info.value, "error_code", None) == MEDIA_STORAGE_UNAVAILABLE
