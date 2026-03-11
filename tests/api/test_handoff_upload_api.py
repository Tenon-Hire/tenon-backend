from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.routers.submissions_routes import detail as submissions_detail_route
from app.core.errors import MEDIA_STORAGE_UNAVAILABLE, REQUEST_TOO_LARGE
from app.core.settings import settings
from app.domains import Job, RecordingAsset, Submission, Transcript
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
)
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import (
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_READY,
)
from app.services.media.transcription_jobs import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    transcribe_recording_idempotency_key,
)
from app.services.scheduling.day_windows import serialize_day_windows
from tests.factories import (
    create_candidate_session,
    create_company,
    create_recruiter,
    create_simulation,
    create_submission,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _fake_storage_provider() -> FakeStorageMediaProvider:
    provider = get_storage_media_provider()
    assert isinstance(provider, FakeStorageMediaProvider)
    return provider


def _set_closed_windows(candidate_session) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    window_start = now - timedelta(days=2)
    window_end = now - timedelta(days=1)
    candidate_session.scheduled_start_at = window_start
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(
        [
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
            for day_index in range(1, 6)
        ]
    )


@pytest.mark.asyncio
async def test_handoff_upload_init_success(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-init@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recordingId"].startswith("rec_")
    assert "upload?" in body["uploadUrl"]
    assert body["expiresInSeconds"] == 900

    recording = (
        await async_session.execute(
            select(RecordingAsset).where(RecordingAsset.task_id == task.id)
        )
    ).scalar_one()
    assert recording.status == RECORDING_ASSET_STATUS_UPLOADING
    assert recording.candidate_session_id == candidate_session.id
    assert recording.content_type == "video/mp4"


@pytest.mark.asyncio
async def test_handoff_upload_init_forbidden_for_non_candidate_token(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-token@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(
            candidate_session, token=f"recruiter:{recruiter.email}"
        ),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 100,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_handoff_upload_init_rejects_invalid_content_type_and_size(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-invalid@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    bad_type = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "application/pdf",
            "sizeBytes": 1_024,
            "filename": "demo.pdf",
        },
    )
    assert bad_type.status_code == 422

    too_big = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 100 * 1024 * 1024 + 1,
            "filename": "demo.mp4",
        },
    )
    assert too_big.status_code == 413
    assert too_big.json()["errorCode"] == "REQUEST_TOO_LARGE"


@pytest.mark.asyncio
async def test_handoff_upload_init_storage_failure_maps_to_media_storage_unavailable(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="handoff-init-storage-failure@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    provider = _fake_storage_provider()

    def _raise_storage_error(*args, **kwargs):
        del args, kwargs
        raise StorageMediaError("storage down")

    monkeypatch.setattr(provider, "create_signed_upload_url", _raise_storage_error)

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1234,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 502, response.text
    assert response.json()["errorCode"] == MEDIA_STORAGE_UNAVAILABLE


@pytest.mark.asyncio
async def test_handoff_upload_complete_is_idempotent_and_creates_transcript(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-complete@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    first_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert first_complete.status_code == 200, first_complete.text
    assert first_complete.json()["status"] == RECORDING_ASSET_STATUS_UPLOADED

    second_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert second_complete.status_code == 200, second_complete.text
    assert second_complete.json()["status"] == RECORDING_ASSET_STATUS_UPLOADED

    recording_after = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    transcript = (
        await async_session.execute(
            select(Transcript).where(Transcript.recording_id == recording_after.id)
        )
    ).scalar_one()
    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == task.id,
            )
        )
    ).scalar_one()
    jobs = (
        (
            await async_session.execute(
                select(Job).where(
                    Job.job_type == TRANSCRIBE_RECORDING_JOB_TYPE,
                    Job.idempotency_key
                    == transcribe_recording_idempotency_key(recording_after.id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert recording_after.status == RECORDING_ASSET_STATUS_UPLOADED
    assert transcript.status == TRANSCRIPT_STATUS_PENDING
    assert submission.recording_id == recording_after.id
    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_handoff_status_returns_recording_and_transcript(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-status@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_536,
            "filename": "status.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )
    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 200, complete_response.text

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == recording_id
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_PENDING


@pytest.mark.asyncio
async def test_handoff_status_uses_latest_attempt_when_resubmission_is_in_progress(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-status-latest-attempt@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    first_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "first.mp4",
        },
    )
    assert first_init.status_code == 200, first_init.text
    first_recording = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert first_recording is not None
    _fake_storage_provider().set_object_metadata(
        first_recording.storage_key,
        content_type=first_recording.content_type,
        size_bytes=first_recording.bytes,
    )
    first_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": first_init.json()["recordingId"]},
    )
    assert first_complete.status_code == 200, first_complete.text

    second_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "second.mp4",
        },
    )
    assert second_init.status_code == 200, second_init.text
    assert second_init.json()["recordingId"] != first_init.json()["recordingId"]

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == second_init.json()["recordingId"]
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADING
    assert body["transcript"] is None


@pytest.mark.asyncio
async def test_handoff_upload_init_returns_task_window_closed_when_outside_window(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-window-init@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=False,
    )
    _set_closed_windows(candidate_session)
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "demo.mp4",
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["errorCode"] == "TASK_WINDOW_CLOSED"


@pytest.mark.asyncio
async def test_handoff_upload_complete_returns_task_window_closed_when_outside_window(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-window-complete@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    _set_closed_windows(candidate_session)
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert response.status_code == 409, response.text
    assert response.json()["errorCode"] == "TASK_WINDOW_CLOSED"


@pytest.mark.asyncio
async def test_handoff_status_remains_available_after_window_closes_for_submitted_recording(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-status-post-cutoff@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "cutoff-status.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id},
    )
    assert complete_response.status_code == 200, complete_response.text

    _set_closed_windows(candidate_session)
    await async_session.commit()

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["recording"]["recordingId"] == recording_id
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_PENDING


@pytest.mark.asyncio
async def test_handoff_resubmission_replaces_submission_pointer_and_preserves_history(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-resubmit@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    first_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_111,
            "filename": "first.mp4",
        },
    )
    assert first_init.status_code == 200, first_init.text
    first_recording = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert first_recording is not None
    _fake_storage_provider().set_object_metadata(
        first_recording.storage_key,
        content_type=first_recording.content_type,
        size_bytes=first_recording.bytes,
    )
    first_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": first_init.json()["recordingId"]},
    )
    assert first_complete.status_code == 200, first_complete.text

    second_init = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_222,
            "filename": "second.mp4",
        },
    )
    assert second_init.status_code == 200, second_init.text
    second_recording = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert second_recording is not None
    assert second_recording.id != first_recording.id
    _fake_storage_provider().set_object_metadata(
        second_recording.storage_key,
        content_type=second_recording.content_type,
        size_bytes=second_recording.bytes,
    )
    second_complete = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": second_init.json()["recordingId"]},
    )
    assert second_complete.status_code == 200, second_complete.text

    submission = (
        await async_session.execute(
            select(Submission).where(
                Submission.candidate_session_id == candidate_session.id,
                Submission.task_id == task.id,
            )
        )
    ).scalar_one()
    first_transcript = (
        await async_session.execute(
            select(Transcript).where(Transcript.recording_id == first_recording.id)
        )
    ).scalar_one()
    second_transcript = (
        await async_session.execute(
            select(Transcript).where(Transcript.recording_id == second_recording.id)
        )
    ).scalar_one()
    assert submission.recording_id == second_recording.id
    assert first_transcript.id != second_transcript.id

    status_response = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert status_response.status_code == 200, status_response.text
    assert (
        status_response.json()["recording"]["recordingId"]
        == second_init.json()["recordingId"]
    )


@pytest.mark.asyncio
async def test_handoff_upload_complete_rejects_missing_uploaded_object(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-missing-object@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1_024,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 422
    assert complete_response.json()["detail"] == "Uploaded object not found"


@pytest.mark.asyncio
async def test_handoff_upload_complete_rejects_oversize_uploaded_object(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="handoff-size-oversize@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 1_024)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 512,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=2_048,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 413
    assert complete_response.json()["errorCode"] == REQUEST_TOO_LARGE


@pytest.mark.asyncio
async def test_handoff_upload_complete_rejects_size_mismatch(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-size-mismatch@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 4_096,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes + 1,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 422
    assert (
        complete_response.json()["detail"]
        == "Uploaded object size does not match expected size"
    )


@pytest.mark.asyncio
async def test_handoff_upload_complete_rejects_content_type_mismatch(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="handoff-type-mismatch@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset).where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
            )
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type="video/webm",
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 422
    assert (
        complete_response.json()["detail"]
        == "Uploaded object content type does not match expected contentType"
    )


@pytest.mark.asyncio
async def test_handoff_upload_complete_storage_failure_maps_to_media_storage_unavailable(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="handoff-complete-storage-failure@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    headers = candidate_header_factory(candidate_session)

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2_048,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text

    provider = _fake_storage_provider()

    def _raise_storage_error(*args, **kwargs):
        del args, kwargs
        raise StorageMediaError("storage down")

    monkeypatch.setattr(provider, "get_object_metadata", _raise_storage_error)

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 502
    assert complete_response.json()["errorCode"] == MEDIA_STORAGE_UNAVAILABLE


@pytest.mark.asyncio
async def test_handoff_upload_complete_forbidden_for_other_candidate(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-owner@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session_a = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="candidate-a@test.com",
        status="in_progress",
        with_default_schedule=True,
    )
    candidate_session_b = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="candidate-b@test.com",
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=candidate_header_factory(candidate_session_a),
        json={
            "contentType": "video/mp4",
            "sizeBytes": 512,
            "filename": "demo.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_id = init_response.json()["recordingId"]

    forbidden = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=candidate_header_factory(candidate_session_b),
        json={"recordingId": recording_id},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_handoff_upload_complete_missing_recording_returns_404(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="handoff-missing@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=candidate_header_factory(candidate_session),
        json={"recordingId": "rec_999999"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_recruiter_detail_includes_recording_and_transcript(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="handoff-detail@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff summary",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/seed.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="hello world transcript",
        segments_json=[{"startMs": 0, "endMs": 1000, "text": "hello"}],
        model_name="mock-stt-v1",
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{recording.id}"
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert body["recording"]["downloadUrl"] is not None
    assert "download?" in body["recording"]["downloadUrl"]
    assert body["transcript"]["status"] == TRANSCRIPT_STATUS_READY
    assert body["transcript"]["modelName"] == "mock-stt-v1"
    assert body["transcript"]["segments"] == [
        {"startMs": 0, "endMs": 1000, "text": "hello"}
    ]
    assert body["handoff"]["recordingId"] == f"rec_{recording.id}"
    assert body["handoff"]["downloadUrl"] is not None
    assert body["handoff"]["transcript"]["status"] == TRANSCRIPT_STATUS_READY


@pytest.mark.asyncio
async def test_recruiter_detail_uses_submission_recording_pointer_not_latest_attempt(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="handoff-pointer@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff summary",
    )
    first_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/first.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=first_recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="first transcript",
        segments_json=[{"startMs": 0, "endMs": 1000, "text": "first"}],
        model_name="mock-stt-v1",
        commit=True,
    )

    # Later recording exists but is not linked by submission.recording_id.
    latest_recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/later.mp4"
        ),
        content_type="video/mp4",
        bytes_count=8_192,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=latest_recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="latest transcript",
        segments_json=[{"startMs": 0, "endMs": 1000, "text": "latest"}],
        model_name="mock-stt-v1",
        commit=True,
    )

    submission.recording_id = first_recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{first_recording.id}"
    assert body["transcript"]["text"] == "first transcript"


@pytest.mark.asyncio
async def test_recruiter_detail_uploaded_recording_download_url_unavailable_on_storage_error(
    async_client, async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="handoff-detail-storage@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff summary",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/seed.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    class _BrokenProvider:
        def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
            del key, expires_seconds
            raise StorageMediaError("boom")

    monkeypatch.setattr(
        submissions_detail_route,
        "get_storage_media_provider",
        lambda: _BrokenProvider(),
    )

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Media storage unavailable"
    assert response.json()["errorCode"] == MEDIA_STORAGE_UNAVAILABLE


@pytest.mark.asyncio
async def test_recruiter_detail_includes_recording_without_download_url_when_not_downloadable(
    async_client, async_session
):
    recruiter = await create_recruiter(
        async_session, email="handoff-detail-uploading@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff summary",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/seed-uploading.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADING,
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADING
    assert body["recording"]["downloadUrl"] is None
    assert body["transcript"] is None
    assert body["handoff"]["recordingId"] == f"rec_{recording.id}"
    assert body["handoff"]["downloadUrl"] is None


@pytest.mark.asyncio
async def test_recruiter_same_company_can_fetch_submission_detail(
    async_client, async_session
):
    company = await create_company(async_session, name="Shared Co")
    owner = await create_recruiter(
        async_session,
        email="company-owner@test.com",
        company=company,
    )
    teammate = await create_recruiter(
        async_session,
        email="company-teammate@test.com",
        company=company,
    )
    sim, tasks = await create_simulation(async_session, created_by=owner)
    candidate_session = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[0],
        content_text="answer",
    )

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": teammate.email},
    )
    assert response.status_code == 200, response.text
