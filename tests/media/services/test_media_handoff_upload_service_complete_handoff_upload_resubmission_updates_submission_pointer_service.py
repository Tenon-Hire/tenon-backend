from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_complete_handoff_upload_resubmission_updates_submission_pointer(
    async_session,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-resubmit-pointer@test.com",
        consented=True,
    )
    candidate_session_id = candidate_session.id
    task_id = task.id
    provider = FakeStorageMediaProvider()
    first, _u1, _e1 = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="first.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        first.storage_key,
        content_type=first.content_type,
        size_bytes=first.bytes,
    )
    await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{first.id}",
        storage_provider=provider,
    )
    initial_submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert initial_submission is not None
    assert initial_submission.recording_id == first.id

    second, _u2, _e2 = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="second.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        second.storage_key,
        content_type=second.content_type,
        size_bytes=second.bytes,
    )
    second_recording_id = second.id
    await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{second.id}",
        storage_provider=provider,
    )
    async_session.expire_all()
    refreshed_submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
    )
    assert refreshed_submission is not None
    assert refreshed_submission.id == initial_submission.id
    assert refreshed_submission.recording_id == second_recording_id
