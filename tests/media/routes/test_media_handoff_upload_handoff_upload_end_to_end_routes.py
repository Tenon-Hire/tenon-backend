from __future__ import annotations

from urllib.parse import urlsplit

import pytest

from app.config import settings
from app.integrations.storage_media import get_storage_media_provider
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
)
from tests.media.routes.media_handoff_upload_api_utils import *


@pytest.mark.asyncio
async def test_handoff_upload_end_to_end_uses_configured_media_base_and_exposes_job_state(
    async_client, async_session, candidate_header_factory, monkeypatch
):
    monkeypatch.setattr(
        settings.storage_media,
        "MEDIA_FAKE_BASE_URL",
        "https://media.example.test/api/recordings/storage/fake",
    )
    get_storage_media_provider.cache_clear()
    try:
        talent_partner = await create_talent_partner(
            async_session, email="handoff-e2e@test.com"
        )
        sim, tasks = await create_trial(async_session, created_by=talent_partner)
        task = _handoff_task(tasks)
        candidate_session = await create_candidate_session(
            async_session,
            trial=sim,
            status="in_progress",
            with_default_schedule=True,
            **CONSENT_KWARGS,
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
        init_body = init_response.json()
        assert init_body["uploadUrl"].startswith(
            "https://media.example.test/api/recordings/storage/fake/upload?"
        )

        upload_url = urlsplit(init_body["uploadUrl"])
        upload_response = await async_client.put(
            f"{upload_url.path}?{upload_url.query}",
            content=b"x" * 1_024,
        )
        assert upload_response.status_code == 204, upload_response.text

        recording = (
            await async_session.execute(
                select(RecordingAsset).where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
            )
        ).scalar_one()
        assert recording.status == RECORDING_ASSET_STATUS_UPLOADING

        complete_response = await async_client.post(
            f"/api/tasks/{task.id}/handoff/upload/complete",
            headers=headers,
            json={"recordingId": init_body["recordingId"]},
        )
        assert complete_response.status_code == 200, complete_response.text

        await async_session.refresh(recording)
        transcript = await transcripts_repo.get_by_recording_id(
            async_session, recording.id
        )
        submission = (
            await async_session.execute(
                select(Submission).where(
                    Submission.candidate_session_id == candidate_session.id,
                    Submission.task_id == task.id,
                )
            )
        ).scalar_one()
        job = (
            await async_session.execute(
                select(Job).where(
                    Job.job_type == TRANSCRIBE_RECORDING_JOB_TYPE,
                    Job.idempotency_key
                    == transcribe_recording_idempotency_key(recording.id),
                )
            )
        ).scalar_one()

        assert recording.status == RECORDING_ASSET_STATUS_UPLOADED
        assert transcript is not None
        assert transcript.status == TRANSCRIPT_STATUS_PENDING
        assert job.status == JOB_STATUS_QUEUED
        assert job.max_attempts == 7

        status_response = await async_client.get(
            f"/api/tasks/{task.id}/handoff/status",
            headers=headers,
        )
        assert status_response.status_code == 200, status_response.text
        status_body = status_response.json()
        assert status_body["recording"]["downloadUrl"].startswith(
            "https://media.example.test/api/recordings/storage/fake/download?"
        )
        assert status_body["transcript"]["status"] == TRANSCRIPT_STATUS_PENDING
        assert status_body["transcript"]["jobStatus"] == JOB_STATUS_QUEUED
        assert status_body["transcript"]["jobAttempt"] == 0
        assert status_body["transcript"]["jobMaxAttempts"] == 7
        assert status_body["transcript"]["retryable"] is True

        detail_response = await async_client.get(
            f"/api/submissions/{submission.id}",
            headers={"x-dev-user-email": talent_partner.email},
        )
        assert detail_response.status_code == 200, detail_response.text
        detail_body = detail_response.json()
        assert detail_body["recording"]["downloadUrl"].startswith(
            "https://media.example.test/api/recordings/storage/fake/download?"
        )
        assert detail_body["transcript"]["status"] == TRANSCRIPT_STATUS_PENDING
        assert detail_body["transcript"]["jobStatus"] == JOB_STATUS_QUEUED
        assert detail_body["transcript"]["retryable"] is True
    finally:
        get_storage_media_provider.cache_clear()
