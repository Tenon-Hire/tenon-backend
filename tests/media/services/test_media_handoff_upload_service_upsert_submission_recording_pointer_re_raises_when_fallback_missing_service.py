from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_upsert_submission_recording_pointer_re_raises_when_fallback_missing(
    async_session, monkeypatch
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-upsert-reraise@test.com",
    )

    async def _raise_integrity(*args, **kwargs):
        del args, kwargs
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(submissions_repo, "upsert_handoff_submission", _raise_integrity)

    with pytest.raises(IntegrityError):
        await _upsert_submission_recording_pointer(
            async_session,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            recording_id=999,
            submitted_at=datetime.now(UTC),
        )
