from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_READY,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_READY,
)
from app.media.services.media_services_media_transcription_jobs_service import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    transcribe_recording_idempotency_key,
)
from app.shared.jobs import worker
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
    Job,
)
from app.submissions.repositories import repository as submissions_repo


def session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


async def assert_transcription_job_and_outputs(
    async_client,
    async_session: AsyncSession,
    *,
    talent_partner_email: str,
    recording,
    recording_id_value: str,
    candidate_session_id: int,
    task_id: int,
) -> None:
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
    recording_id, job_id = recording.id, job.id

    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker(async_session),
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
        async_session, candidate_session_id=candidate_session_id, task_id=task_id
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
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert detail_response.status_code == 200, detail_response.text
    body = detail_response.json()
    assert body["handoff"]["recordingId"] == recording_id_value
    assert body["handoff"]["downloadUrl"] is not None
    assert body["handoff"]["transcript"]["status"] == TRANSCRIPT_STATUS_READY
