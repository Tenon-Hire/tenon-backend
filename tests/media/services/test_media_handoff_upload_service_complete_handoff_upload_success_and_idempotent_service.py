from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_success_and_idempotent(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-idempotent@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        duration_seconds=600,
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
        duration_seconds=600,
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
    submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    jobs = (
        (
            await async_session.execute(
                select(Job).where(
                    Job.job_type == TRANSCRIBE_RECORDING_JOB_TYPE,
                    Job.idempotency_key
                    == transcribe_recording_idempotency_key(recording.id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert first.status == "uploaded"
    assert second.status == "uploaded"
    assert transcript is not None
    assert transcript.status == TRANSCRIPT_STATUS_PENDING
    assert submission is not None
    assert submission.recording_id == recording.id
    assert len(jobs) == 1
    assert jobs[0].max_attempts == 7
    assert jobs[0].payload_json["companyId"] == jobs[0].company_id


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_missing_duration_metadata(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-missing-duration@test.com",
        consented=True,
    )

    class _MissingDurationProvider(FakeStorageMediaProvider):
        def get_object_metadata(self, key: str):
            metadata = super().get_object_metadata(key)
            if metadata is None:
                return None
            return SimpleNamespace(
                content_type=metadata.content_type,
                size_bytes=metadata.size_bytes,
                duration_seconds=None,
            )

    provider = _MissingDurationProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="missing-duration.mp4",
        duration_seconds=600,
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
        duration_seconds=600,
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
    assert exc_info.value.detail == "Uploaded recording is missing duration metadata"


@pytest.mark.asyncio
async def test_complete_handoff_upload_allows_supplemental_without_duration_metadata(
    async_session,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-supplemental-duration@test.com",
        consented=True,
    )

    class _NoDurationProvider(FakeStorageMediaProvider):
        def get_object_metadata(self, key: str):
            metadata = super().get_object_metadata(key)
            if metadata is None:
                return None
            return SimpleNamespace(
                content_type=metadata.content_type,
                size_bytes=metadata.size_bytes,
                duration_seconds=None,
            )

    provider = _NoDurationProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="application/pdf",
        size_bytes=2048,
        filename="slides.pdf",
        asset_kind="supplemental",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    completed = await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{recording.id}",
        storage_provider=provider,
    )
    assert completed.status == "uploaded"
