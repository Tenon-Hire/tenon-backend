from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_upsert_submission_recording_pointer_integrity_race_no_change(
    async_session, monkeypatch
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-upsert-race-no-change@test.com",
    )
    provider = FakeStorageMediaProvider()
    first, _u1, _e1 = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1000,
        filename="race-same.mp4",
        storage_provider=provider,
    )
    existing = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        recording_id=first.id,
    )

    async def _upsert(*args, **kwargs):
        del args, kwargs
        return existing.id

    monkeypatch.setattr(submissions_repo, "upsert_handoff_submission", _upsert)

    resolved_id = await _upsert_submission_recording_pointer(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        recording_id=first.id,
        submitted_at=datetime.now(UTC),
    )
    assert resolved_id == existing.id
