from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


@pytest.mark.asyncio
async def test_delete_recording_asset_logs_without_sensitive_payload(
    async_session,
    caplog,
):
    caplog.set_level(
        "INFO", logger="app.media.services.media_services_media_privacy_service"
    )
    talent_partner = await create_talent_partner(
        async_session,
        email="privacy-delete-log@test.com",
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, trial=sim)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/delete-log.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1234,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="do-not-log-this-transcript",
        commit=True,
    )

    await delete_recording_asset(
        async_session,
        recording_id=recording.id,
        candidate_session=candidate_session,
    )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert f"recording deleted recordingId={recording.id}" in log_text
    assert "do-not-log-this-transcript" not in log_text
    assert "https://" not in log_text
