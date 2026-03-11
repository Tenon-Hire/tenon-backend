from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.routers.submissions_routes import detail as detail_route
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import RECORDING_ASSET_STATUS_UPLOADED
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_READY
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


@pytest.mark.asyncio
async def test_submission_detail_route_includes_media_payload(async_session):
    recruiter = await create_recruiter(
        async_session, email="detail-route-success@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
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
            "recordings/detail.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="hello transcript",
        model_name="test-model",
        commit=True,
    )

    payload = await detail_route.get_submission_detail_route(
        submission_id=submission.id,
        db=async_session,
        user=recruiter,
    )

    assert payload.recording is not None
    assert payload.recording.recordingId == f"rec_{recording.id}"
    assert payload.recording.downloadUrl is not None
    assert payload.transcript is not None
    assert payload.transcript.status == TRANSCRIPT_STATUS_READY


@pytest.mark.asyncio
async def test_submission_detail_route_surfaces_storage_error(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session, email="detail-route-error@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff notes",
    )
    await recordings_repo.create_recording_asset(
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

    class _BrokenProvider:
        def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
            del key, expires_seconds
            raise StorageMediaError("storage unavailable")

    monkeypatch.setattr(detail_route, "get_storage_media_provider", _BrokenProvider)

    with pytest.raises(HTTPException) as exc_info:
        await detail_route.get_submission_detail_route(
            submission_id=submission.id,
            db=async_session,
            user=recruiter,
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Media storage unavailable"
