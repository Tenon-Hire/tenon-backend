from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.jobs import worker
from app.repositories.jobs.models import JOB_STATUS_QUEUED, JOB_STATUS_SUCCEEDED, Job
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import RECORDING_ASSET_STATUS_READY
from app.repositories.submissions import repository as submissions_repo
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_READY
from app.services.media.transcription_jobs import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    transcribe_recording_idempotency_key,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


@pytest.mark.asyncio
async def test_handoff_upload_complete_enqueue_and_worker_transcribes(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(async_session, email="handoff-int@test.com")
    recruiter_email = recruiter.email
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    candidate_session_id = candidate_session.id
    task_id = task.id
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

    recording_id_value = init_response.json()["recordingId"]
    recording = await recordings_repo.get_latest_for_task_session(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert recording is not None

    from app.integrations.storage_media import get_storage_media_provider

    provider = get_storage_media_provider()
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_id_value},
    )
    assert complete_response.status_code == 200, complete_response.text

    job = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == TRANSCRIBE_RECORDING_JOB_TYPE,
                Job.idempotency_key
                == transcribe_recording_idempotency_key(recording.id),
            )
        )
    ).scalar_one()
    assert job.status == JOB_STATUS_QUEUED
    recording_id = recording.id
    job_id = job.id

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=_session_maker(async_session),
            worker_id="handoff-int-worker",
            now=datetime.now(UTC),
        )
        assert handled is True
    finally:
        worker.clear_handlers()

    async_session.expire_all()
    refreshed_job = (
        await async_session.execute(select(Job).where(Job.id == job_id))
    ).scalar_one()
    assert refreshed_job.status == JOB_STATUS_SUCCEEDED

    refreshed_recording = await recordings_repo.get_by_id(async_session, recording_id)
    transcript = await transcripts_repo.get_by_recording_id(async_session, recording_id)
    submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
    )
    assert refreshed_recording is not None
    assert refreshed_recording.status == RECORDING_ASSET_STATUS_READY
    assert transcript is not None
    assert transcript.status == TRANSCRIPT_STATUS_READY
    assert transcript.text
    assert submission is not None
    assert submission.recording_id == recording_id

    detail_response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter_email},
    )
    assert detail_response.status_code == 200, detail_response.text
    body = detail_response.json()
    assert body["handoff"]["recordingId"] == recording_id_value
    assert body["handoff"]["downloadUrl"] is not None
    assert body["handoff"]["transcript"]["status"] == TRANSCRIPT_STATUS_READY
