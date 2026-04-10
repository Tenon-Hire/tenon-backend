from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_transcript_repository_commit_true_paths(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="transcript-pass2@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks[0].id,
        storage_key="recordings/pass2.mp4",
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    transcript, created = await transcripts_repo.get_or_create_transcript(
        async_session,
        recording_id=recording.id,
        status="pending",
        commit=True,
    )
    assert created is True
    assert transcript.id is not None

    deleted = await transcripts_repo.mark_deleted(
        async_session,
        transcript=transcript,
        commit=True,
    )
    assert deleted.deleted_at is not None

    removed_count = await transcripts_repo.hard_delete_by_recording_id(
        async_session,
        recording.id,
        commit=True,
    )
    assert removed_count == 1
