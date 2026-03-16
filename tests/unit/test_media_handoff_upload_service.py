from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.errors import MEDIA_STORAGE_UNAVAILABLE, REQUEST_TOO_LARGE
from app.core.settings import settings
from app.domains import Job
from app.integrations.storage_media import FakeStorageMediaProvider
from app.integrations.storage_media.base import StorageMediaError
from app.repositories.submissions import repository as submissions_repo
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_PENDING
from app.services.media.handoff_upload import (
    _resolve_company_id,
    _upsert_submission_recording_pointer,
    complete_handoff_upload,
    get_handoff_status,
    init_handoff_upload,
)
from app.services.media.transcription_jobs import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    transcribe_recording_idempotency_key,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)

CONSENT_KWARGS = {"consent_version": "mvp1", "ai_notice_version": "mvp1"}


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _non_handoff_task(tasks):
    return next(task for task in tasks if task.type != "handoff")


async def _setup_handoff_context(
    async_session,
    email: str,
    *,
    consented: bool = False,
):
    recruiter = await create_recruiter(async_session, email=email)
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
        **(CONSENT_KWARGS if consented else {}),
    )
    await async_session.commit()
    return _handoff_task(tasks), _non_handoff_task(tasks), candidate_session


@pytest.mark.asyncio
async def test_init_handoff_upload_success(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-success@test.com",
    )
    provider = FakeStorageMediaProvider()

    recording, upload_url, expires_seconds = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="demo.mp4",
        storage_provider=provider,
    )

    assert recording.id > 0
    assert recording.status == "uploading"
    assert upload_url.startswith("https://fake-storage.local/upload?")
    assert expires_seconds > 0


@pytest.mark.asyncio
async def test_init_handoff_upload_rejects_non_handoff_task(async_session):
    _, non_handoff_task, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-not-handoff@test.com",
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await init_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=non_handoff_task.id,
            content_type="video/mp4",
            size_bytes=1024,
            filename="demo.mp4",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert "handoff tasks" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_init_handoff_upload_surfaces_storage_unavailable(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-init-storage-error@test.com",
    )

    class _BrokenProvider(FakeStorageMediaProvider):
        def create_signed_upload_url(
            self, key: str, content_type: str, size_bytes: int, expires_seconds: int
        ) -> str:
            del key, content_type, size_bytes, expires_seconds
            raise StorageMediaError("storage down")

    with pytest.raises(HTTPException) as exc_info:
        await init_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            content_type="video/mp4",
            size_bytes=1024,
            filename="demo.mp4",
            storage_provider=_BrokenProvider(),
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Media storage unavailable"
    assert getattr(exc_info.value, "error_code", None) == MEDIA_STORAGE_UNAVAILABLE


@pytest.mark.asyncio
async def test_complete_handoff_upload_success_and_idempotent(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-idempotent@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    first = await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{recording.id}",
        storage_provider=provider,
    )
    second = await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{recording.id}",
        storage_provider=provider,
    )

    transcript = await transcripts_repo.get_by_recording_id(async_session, recording.id)
    submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    jobs = (
        (
            await async_session.execute(
                select(Job).where(
                    Job.job_type == TRANSCRIBE_RECORDING_JOB_TYPE,
                    Job.idempotency_key
                    == transcribe_recording_idempotency_key(recording.id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert first.status == "uploaded"
    assert second.status == "uploaded"
    assert transcript is not None
    assert transcript.status == TRANSCRIPT_STATUS_PENDING
    assert submission is not None
    assert submission.recording_id == recording.id
    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_missing_uploaded_object(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-missing-object@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=512,
        filename="demo.mp4",
        storage_provider=provider,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Uploaded object not found"


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_size_mismatch(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-size-mismatch@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes + 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Uploaded object size does not match expected size"


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_oversize_uploaded_object(
    async_session,
    monkeypatch,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-size-oversize@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    monkeypatch.setattr(settings.storage_media, "MEDIA_MAX_UPLOAD_BYTES", 1024)
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes + 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 413
    assert getattr(exc_info.value, "error_code", None) == REQUEST_TOO_LARGE


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_content_type_mismatch(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-type-mismatch@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type="video/webm",
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "Uploaded object content type does not match expected contentType"
    )


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_invalid_recording_id(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-invalid-id@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value="not-a-recording-id",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 422
    assert "recordingId" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_missing_recording(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-missing-recording@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value="rec_999999",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Recording asset not found"


@pytest.mark.asyncio
async def test_complete_handoff_upload_requires_consent(async_session):
    recruiter = await create_recruiter(
        async_session,
        email="service-complete-no-consent@test.com",
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Consent is required before upload completion"


@pytest.mark.asyncio
async def test_complete_handoff_upload_rejects_other_candidate(async_session):
    recruiter = await create_recruiter(async_session, email="service-owner@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="owner@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    other_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="other@test.com",
        status="in_progress",
        with_default_schedule=True,
        **CONSENT_KWARGS,
    )
    await async_session.commit()

    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=2048,
        filename="demo.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=other_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=provider,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_complete_handoff_upload_surfaces_storage_unavailable(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-complete-storage-error@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=256,
        filename="demo.mp4",
        storage_provider=provider,
    )

    class _BrokenMetadataProvider(FakeStorageMediaProvider):
        def get_object_metadata(self, key: str):
            del key
            raise StorageMediaError("down")

    with pytest.raises(HTTPException) as exc_info:
        await complete_handoff_upload(
            async_session,
            candidate_session=candidate_session,
            task_id=task.id,
            recording_id_value=f"rec_{recording.id}",
            storage_provider=_BrokenMetadataProvider(),
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Media storage unavailable"
    assert getattr(exc_info.value, "error_code", None) == MEDIA_STORAGE_UNAVAILABLE


@pytest.mark.asyncio
async def test_get_handoff_status_returns_latest_attempt_over_submission_pointer(
    async_session,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-status-pointer@test.com",
        consented=True,
    )
    provider = FakeStorageMediaProvider()
    first_recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1024,
        filename="first.mp4",
        storage_provider=provider,
    )
    provider.set_object_metadata(
        first_recording.storage_key,
        content_type=first_recording.content_type,
        size_bytes=first_recording.bytes,
    )
    await complete_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        recording_id_value=f"rec_{first_recording.id}",
        storage_provider=provider,
    )

    # New init creates a newer recording attempt; candidate status should
    # reflect this latest in-progress attempt immediately.
    latest_recording, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1536,
        filename="second.mp4",
        storage_provider=provider,
    )

    recording, transcript = await get_handoff_status(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
    )
    assert recording is not None
    assert recording.id == latest_recording.id
    assert recording.status == "uploading"
    assert transcript is None


@pytest.mark.asyncio
async def test_get_handoff_status_falls_back_to_latest_recording_without_submission(
    async_session,
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-status-fallback@test.com",
    )
    provider = FakeStorageMediaProvider()
    latest, _upload_url, _expires = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=777,
        filename="latest.mp4",
        storage_provider=provider,
    )

    recording, transcript = await get_handoff_status(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
    )
    assert recording is not None
    assert recording.id == latest.id
    assert transcript is None


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


@pytest.mark.asyncio
async def test_upsert_submission_recording_pointer_handles_integrity_race(
    async_session, monkeypatch
):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-upsert-race@test.com",
    )
    provider = FakeStorageMediaProvider()
    first, _u1, _e1 = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1000,
        filename="race-a.mp4",
        storage_provider=provider,
    )
    second, _u2, _e2 = await init_handoff_upload(
        async_session,
        candidate_session=candidate_session,
        task_id=task.id,
        content_type="video/mp4",
        size_bytes=1200,
        filename="race-b.mp4",
        storage_provider=provider,
    )
    existing = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        recording_id=first.id,
    )

    original_get = submissions_repo.get_by_candidate_session_task
    state = {"count": 0}

    async def _racy_get(
        db,
        *,
        candidate_session_id: int,
        task_id: int,
        for_update: bool = False,
    ):
        state["count"] += 1
        if state["count"] == 1:
            return None
        return await original_get(
            db,
            candidate_session_id=candidate_session_id,
            task_id=task_id,
            for_update=for_update,
        )

    async def _raise_integrity(*args, **kwargs):
        del args, kwargs
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(submissions_repo, "get_by_candidate_session_task", _racy_get)
    monkeypatch.setattr(submissions_repo, "create_handoff_submission", _raise_integrity)

    resolved, changed = await _upsert_submission_recording_pointer(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        recording_id=second.id,
        submitted_at=datetime.now(UTC),
    )
    assert changed is True
    assert resolved.id == existing.id
    assert resolved.recording_id == second.id


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

    async def _missing_submission(
        db,
        *,
        candidate_session_id: int,
        task_id: int,
        for_update: bool = False,
    ):
        del db, candidate_session_id, task_id, for_update
        return None

    monkeypatch.setattr(submissions_repo, "create_handoff_submission", _raise_integrity)
    monkeypatch.setattr(
        submissions_repo,
        "get_by_candidate_session_task",
        _missing_submission,
    )

    with pytest.raises(IntegrityError):
        await _upsert_submission_recording_pointer(
            async_session,
            candidate_session_id=candidate_session.id,
            task_id=task.id,
            recording_id=999,
            submitted_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_resolve_company_id_raises_when_simulation_missing(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-company-missing@test.com",
    )
    candidate_session.__dict__.pop("simulation", None)

    with pytest.raises(HTTPException) as exc_info:
        await _resolve_company_id(
            async_session,
            candidate_session=candidate_session,
            simulation_id=task.simulation_id + 999_999,
        )
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Simulation metadata unavailable"
