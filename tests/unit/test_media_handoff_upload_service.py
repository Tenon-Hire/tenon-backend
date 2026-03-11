from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.integrations.storage_media import FakeStorageMediaProvider
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_PENDING
from app.services.media.handoff_upload import (
    complete_handoff_upload,
    init_handoff_upload,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _non_handoff_task(tasks):
    return next(task for task in tasks if task.type != "handoff")


async def _setup_handoff_context(async_session, email: str):
    recruiter = await create_recruiter(async_session, email=email)
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()
    return _handoff_task(tasks), _non_handoff_task(tasks), candidate_session


@pytest.mark.asyncio
async def test_init_handoff_upload_success(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-success@test.com",
    )
    provider = FakeStorageMediaProvider()

    recording, upload_url, expires_seconds = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="demo.mp4",
        storage_provider=provider,
    )

    assert recording.id > 0
    assert recording.status == "uploading"
    assert upload_url.startswith("https://fake-storage.local/upload?")
    assert expires_seconds > 0


@pytest.mark.asyncio
async def test_init_handoff_upload_rejects_non_handoff_task(async_session):
    _, non_handoff_task, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-not-handoff@test.com",
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await init_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=non_handoff_task.id,
            content_type="video/mp4",
            size_bytes=1024,
            filename="demo.mp4",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert "handoff tasks" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_init_handoff_upload_surfaces_storage_unavailable(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-storage-error@test.com",
    )

    class _BrokenProvider(FakeStorageMediaProvider):
        def create_signed_upload_url(
            self, key: str, content_type: str, size_bytes: int, expires_seconds: int
        ) -> str:
            del key, content_type, size_bytes, expires_seconds
            raise StorageMediaError("storage down")

    with pytest.raises(HTTPException) as exc_info:
        await init_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            content_type="video/mp4",
            size_bytes=1024,
            filename="demo.mp4",
            storage_provider=_BrokenProvider(),
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Media storage unavailable"


@pytest.mark.asyncio
async def test_complete_handoff_upload_success_and_idempotent(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-idempotent@test.com",
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    first = await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{recording.id}",
        storage_provider=provider,
    )
    second = await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{recording.id}",
        storage_provider=provider,
    )

    transcript = await transcripts_repo.get_by_recording_id(async_session, recording.id)
    assert first.status == "uploaded"
    assert second.status == "uploaded"
    assert transcript is not None
    assert transcript.status == TRANSCRIPT_STATUS_PENDING


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_missing_uploaded_object(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-missing-object@test.com",
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=512,
        filename="demo.mp4",
        storage_provider=provider,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Uploaded object not found"


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_size_mismatch(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-size-mismatch@test.com",
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes + 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Uploaded object size does not match expected size"


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_content_type_mismatch(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-type-mismatch@test.com",
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type="video/webm",
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "Uploaded object content type does not match expected contentType"
    )


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_invalid_recording_id(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-invalid-id@test.com",
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value="not-a-recording-id",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert "recordingId" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_missing_recording(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-missing-recording@test.com",
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value="rec_999999",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Recording asset not found"


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_other_candidate(async_session):
    recruiter = await create_recruiter(async_session, email="service-owner@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="owner@test.com",
        status="in_progress",
        with_default_schedule=True,
    )
    other_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="other@test.com",
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=other_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_complete_handoff_upload_surfaces_storage_unavailable(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-storage-error@test.com",
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=256,
        filename="demo.mp4",
        storage_provider=provider,
    )

    class _BrokenMetadataProvider(FakeStorageMediaProvider):
        def get_object_metadata(self, key: str):
            del key
            raise StorageMediaError("down")

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=_BrokenMetadataProvider(),
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Media storage unavailable"
