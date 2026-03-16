from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.settings import settings
from app.integrations.storage_media import FakeStorageMediaProvider
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import (
    RECORDING_ASSET_STATUS_PURGED,
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_READY
from app.services.media.privacy import (
    delete_recording_asset,
    purge_expired_media_assets,
    record_candidate_session_consent,
    require_media_consent,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


@pytest.mark.asyncio
async def test_record_candidate_session_consent_is_idempotent(async_session):
    recruiter = await create_recruiter(async_session, email="privacy-consent@test.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    recorded = await record_candidate_session_consent(
        async_session,
        candidate_session=candidate_session,
        notice_version="mvp1",
        ai_notice_version="mvp1",
    )
    first_timestamp = recorded.consent_timestamp
    assert recorded.consent_version == "mvp1"
    assert first_timestamp is not None

    recorded_again = await record_candidate_session_consent(
        async_session,
        candidate_session=recorded,
        notice_version="mvp1",
        ai_notice_version="mvp1",
    )
    assert recorded_again.consent_timestamp == first_timestamp


@pytest.mark.asyncio
async def test_record_candidate_session_consent_logs_audit_safe_event(
    async_session,
    caplog,
):
    caplog.set_level("INFO", logger="app.services.media.privacy")
    recruiter = await create_recruiter(
        async_session, email="privacy-consent-log@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="consent-log-candidate@test.com",
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    await record_candidate_session_consent(
        async_session,
        candidate_session=candidate_session,
        notice_version="mvp1",
        ai_notice_version="mvp1",
    )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert (
        f"consent recorded candidateSessionId={candidate_session.id} consentVersion=mvp1"
        in log_text
    )
    assert candidate_session.invite_email not in log_text
    assert "https://" not in log_text
    assert "Bearer " not in log_text


@pytest.mark.asyncio
async def test_record_candidate_session_consent_rejects_blank_notice(async_session):
    recruiter = await create_recruiter(
        async_session,
        email="privacy-consent-invalid@test.com",
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await record_candidate_session_consent(
            async_session,
            candidate_session=candidate_session,
            notice_version="   ",
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "noticeVersion is required"


def test_require_media_consent_rejects_missing_values():
    with pytest.raises(HTTPException) as missing_version:
        require_media_consent(
            SimpleNamespace(consent_version=None, consent_timestamp=datetime.now(UTC))
        )
    assert missing_version.value.status_code == 409

    with pytest.raises(HTTPException) as missing_timestamp:
        require_media_consent(
            SimpleNamespace(consent_version="mvp1", consent_timestamp=None)
        )
    assert missing_timestamp.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_recording_asset_soft_deletes_and_hides_transcript(async_session):
    recruiter = await create_recruiter(async_session, email="privacy-delete@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/delete.mp4"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="sensitive transcript",
        segments_json=[{"startMs": 0, "endMs": 1, "text": "hidden"}],
        model_name="model",
        commit=True,
    )

    await delete_recording_asset(
        async_session,
        recording_id=recording.id,
        candidate_session=candidate_session,
    )
    await delete_recording_asset(
        async_session,
        recording_id=recording.id,
        candidate_session=candidate_session,
    )

    refreshed = await recordings_repo.get_by_id(async_session, recording.id)
    transcript = await transcripts_repo.get_by_recording_id(
        async_session,
        recording.id,
        include_deleted=True,
    )

    assert refreshed is not None
    assert refreshed.deleted_at is not None
    assert recordings_repo.is_downloadable(refreshed) is False
    assert transcript is not None
    assert transcript.deleted_at is not None
    assert transcript.text is None
    assert transcript.segments_json is None


@pytest.mark.asyncio
async def test_delete_recording_asset_logs_without_sensitive_payload(
    async_session,
    caplog,
):
    caplog.set_level("INFO", logger="app.services.media.privacy")
    recruiter = await create_recruiter(
        async_session,
        email="privacy-delete-log@test.com",
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)
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


@pytest.mark.asyncio
async def test_delete_recording_asset_forbidden_for_other_candidate(async_session):
    recruiter = await create_recruiter(
        async_session, email="privacy-delete-403@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="owner@test.com",
    )
    other_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="other@test.com",
    )

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=owner_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{owner_session.id}/tasks/{task.id}/"
            "recordings/delete-forbidden.mp4"
        ),
        content_type="video/mp4",
        bytes_count=512,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_recording_asset(
            async_session,
            recording_id=recording.id,
            candidate_session=other_session,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_recording_asset_disabled_and_missing_recording(
    async_session,
    monkeypatch,
):
    recruiter = await create_recruiter(
        async_session,
        email="privacy-delete-disabled@test.com",
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    monkeypatch.setattr(settings.storage_media, "MEDIA_DELETE_ENABLED", False)
    with pytest.raises(HTTPException) as disabled_exc:
        await delete_recording_asset(
            async_session,
            recording_id=123,
            candidate_session=candidate_session,
        )
    assert disabled_exc.value.status_code == 403

    monkeypatch.setattr(settings.storage_media, "MEDIA_DELETE_ENABLED", True)
    with pytest.raises(HTTPException) as missing_exc:
        await delete_recording_asset(
            async_session,
            recording_id=123,
            candidate_session=candidate_session,
        )
    assert missing_exc.value.status_code == 404


@pytest.mark.asyncio
async def test_purge_expired_media_assets_removes_storage_and_transcript(async_session):
    recruiter = await create_recruiter(async_session, email="privacy-purge@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    now = datetime.now(UTC).replace(microsecond=0)
    old_created_at = now - timedelta(days=20)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/purge.mp4"
        ),
        content_type="video/mp4",
        bytes_count=2048,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        created_at=old_created_at,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="purge me",
        commit=True,
    )

    provider = FakeStorageMediaProvider()
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=provider,
        retention_days=10,
        batch_limit=20,
        now=now,
    )

    refreshed = await recordings_repo.get_by_id(async_session, recording.id)
    transcript = await transcripts_repo.get_by_recording_id(
        async_session,
        recording.id,
        include_deleted=True,
    )

    assert result.scanned_count >= 1
    assert recording.id in result.purged_recording_ids
    assert result.purged_count == 1
    assert result.failed_count == 0
    assert provider.get_object_metadata(recording.storage_key) is None
    assert refreshed is not None
    assert refreshed.status == RECORDING_ASSET_STATUS_PURGED
    assert refreshed.purged_at is not None
    assert transcript is None


@pytest.mark.asyncio
async def test_purge_expired_media_assets_logs_without_sensitive_payload(
    async_session,
    caplog,
):
    caplog.set_level("INFO", logger="app.services.media.privacy")
    recruiter = await create_recruiter(
        async_session, email="privacy-purge-log@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(async_session, simulation=sim)

    now = datetime.now(UTC).replace(microsecond=0)
    old_created_at = now - timedelta(days=20)
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/purge-log.mp4"
        ),
        content_type="video/mp4",
        bytes_count=2048,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        created_at=old_created_at,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="do-not-log-this-purge-transcript",
        commit=True,
    )
    provider = FakeStorageMediaProvider()
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=provider,
        retention_days=10,
        batch_limit=20,
        now=now,
    )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert recording.id in result.purged_recording_ids
    assert f"purge executed recordingId={recording.id}" in log_text
    assert "do-not-log-this-purge-transcript" not in log_text
    assert "https://" not in log_text


@pytest.mark.asyncio
async def test_purge_expired_media_assets_skips_missing_and_already_purged(
    async_session,
    monkeypatch,
):
    candidates = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def _expired(*_args, **_kwargs):
        return candidates

    async def _for_update(_db, recording_id: int):
        if recording_id == 1:
            return None
        return SimpleNamespace(
            id=2,
            status=RECORDING_ASSET_STATUS_PURGED,
            purged_at=datetime.now(UTC),
            storage_key="candidate-sessions/1/tasks/1/recordings/purged.mp4",
        )

    monkeypatch.setattr(recordings_repo, "get_expired_for_retention", _expired)
    monkeypatch.setattr(recordings_repo, "get_by_id_for_update", _for_update)

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=FakeStorageMediaProvider(),
        retention_days=1,
        batch_limit=10,
        now=datetime.now(UTC),
    )

    assert result.scanned_count == 2
    assert result.purged_count == 0
    assert result.failed_count == 0


@pytest.mark.asyncio
async def test_purge_expired_media_assets_tracks_storage_and_unexpected_failures(
    async_session,
    monkeypatch,
):
    candidates = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def _expired(*_args, **_kwargs):
        return candidates

    async def _for_update(_db, recording_id: int):
        return SimpleNamespace(
            id=recording_id,
            status=RECORDING_ASSET_STATUS_UPLOADED,
            purged_at=None,
            storage_key=(
                f"candidate-sessions/1/tasks/1/recordings/failure-{recording_id}.mp4"
            ),
        )

    class _BrokenProvider:
        def __init__(self):
            self.calls = 0

        def delete_object(self, key: str) -> None:
            del key
            self.calls += 1
            if self.calls == 1:
                raise StorageMediaError("storage down")
            raise RuntimeError("unexpected failure")

    monkeypatch.setattr(recordings_repo, "get_expired_for_retention", _expired)
    monkeypatch.setattr(recordings_repo, "get_by_id_for_update", _for_update)

    result = await purge_expired_media_assets(
        async_session,
        storage_provider=_BrokenProvider(),
        retention_days=1,
        batch_limit=10,
        now=datetime.now(UTC),
    )

    assert result.scanned_count == 2
    assert result.purged_count == 0
    assert result.failed_count == 2
