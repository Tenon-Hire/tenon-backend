from __future__ import annotations

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
