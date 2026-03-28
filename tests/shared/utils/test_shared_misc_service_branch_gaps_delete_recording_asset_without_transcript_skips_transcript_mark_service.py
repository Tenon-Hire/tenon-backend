from __future__ import annotations

import pytest

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_delete_recording_asset_without_transcript_skips_transcript_mark(
    monkeypatch,
):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=55)
    recording = SimpleNamespace(id=10, candidate_session_id=55, storage_key="k")
    calls = {"mark_transcript_deleted": 0}

    async def _get_by_id_for_update(_db, _recording_id):
        return recording

    async def _mark_deleted(_db, *, recording, now, commit):
        assert recording.id == 10
        assert commit is False

    async def _get_transcript_by_recording_id(_db, _recording_id, include_deleted):
        assert include_deleted is True
        return None

    async def _mark_transcript_deleted(*_args, **_kwargs):
        calls["mark_transcript_deleted"] += 1

    monkeypatch.setattr(
        media_privacy.settings.storage_media, "MEDIA_DELETE_ENABLED", True
    )
    monkeypatch.setattr(
        media_privacy.recordings_repo, "get_by_id_for_update", _get_by_id_for_update
    )
    monkeypatch.setattr(media_privacy.recordings_repo, "mark_deleted", _mark_deleted)
    monkeypatch.setattr(
        media_privacy.transcripts_repo,
        "get_by_recording_id",
        _get_transcript_by_recording_id,
    )
    monkeypatch.setattr(
        media_privacy.transcripts_repo,
        "mark_deleted",
        _mark_transcript_deleted,
    )

    result = await media_privacy.delete_recording_asset(
        db,
        recording_id=10,
        candidate_session=candidate_session,
    )

    assert result is recording
    assert calls["mark_transcript_deleted"] == 0
    assert db.commits == 1
    assert db.refreshes == 1
