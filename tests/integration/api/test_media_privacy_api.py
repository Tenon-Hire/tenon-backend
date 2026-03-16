from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains import CandidateSession, RecordingAsset, Submission
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
)
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import RECORDING_ASSET_STATUS_UPLOADED
from tests.factories import (
    create_candidate_session,
    create_company,
    create_recruiter,
    create_simulation,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _fake_storage_provider() -> FakeStorageMediaProvider:
    provider = get_storage_media_provider()
    assert isinstance(provider, FakeStorageMediaProvider)
    return provider


async def _seed_uploaded_recording(
    async_session,
    *,
    candidate_session,
    task_id: int,
    filename: str,
) -> RecordingAsset:
    return await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task_id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task_id}/"
            f"recordings/{filename}"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )


@pytest.mark.asyncio
async def test_candidate_privacy_consent_endpoint_records_fields(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-consent-api@test.com"
    )
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        consent_version=None,
        consent_timestamp=None,
        ai_notice_version=None,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/candidate/session/{candidate_session.id}/privacy/consent",
        headers=candidate_header_factory(candidate_session),
        json={"noticeVersion": "mvp1"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "consent_recorded"}

    refreshed = await async_session.get(CandidateSession, candidate_session.id)
    assert refreshed is not None
    assert refreshed.consent_version == "mvp1"
    assert refreshed.consent_timestamp is not None
    assert refreshed.ai_notice_version == "mvp1"


@pytest.mark.asyncio
async def test_handoff_upload_complete_blocked_without_consent(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-no-consent@test.com"
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

    headers = candidate_header_factory(candidate_session)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 1024,
            "filename": "consent-required.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text

    provider = _fake_storage_provider()
    recording_asset = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert recording_asset is not None
    provider.set_object_metadata(
        recording_asset.storage_key,
        content_type=recording_asset.content_type,
        size_bytes=recording_asset.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 409
    assert (
        complete_response.json()["detail"]
        == "Consent is required before upload completion"
    )


@pytest.mark.asyncio
async def test_candidate_delete_recording_is_idempotent_and_blocks_recruiter_download(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-delete-api@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    await async_session.commit()

    headers = candidate_header_factory(candidate_session)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": 2048,
            "filename": "delete-me.mp4",
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording_public_id = init_response.json()["recordingId"]

    recording = (
        (
            await async_session.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session.id,
                    RecordingAsset.task_id == task.id,
                )
                .order_by(RecordingAsset.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert recording is not None
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
    )

    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": recording_public_id},
    )
    assert complete_response.status_code == 200, complete_response.text

    submission = (
        (
            await async_session.execute(
                select(Submission).where(
                    Submission.candidate_session_id == candidate_session.id,
                    Submission.task_id == task.id,
                )
            )
        )
        .scalars()
        .first()
    )
    assert submission is not None

    recruiter_before_delete = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert recruiter_before_delete.status_code == 200, recruiter_before_delete.text
    assert recruiter_before_delete.json()["recording"]["downloadUrl"] is not None

    delete_first = await async_client.post(
        f"/api/recordings/{recording_public_id}/delete",
        headers=headers,
    )
    assert delete_first.status_code == 200, delete_first.text
    assert delete_first.json() == {"status": "deleted"}

    delete_second = await async_client.post(
        f"/api/recordings/{recording_public_id}/delete",
        headers=headers,
    )
    assert delete_second.status_code == 200, delete_second.text
    assert delete_second.json() == {"status": "deleted"}

    recruiter_after_delete = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": recruiter.email},
    )
    assert recruiter_after_delete.status_code == 200, recruiter_after_delete.text
    body = recruiter_after_delete.json()
    assert body["recording"]["downloadUrl"] is None
    assert body["transcript"] is None

    candidate_status = await async_client.get(
        f"/api/tasks/{task.id}/handoff/status",
        headers=headers,
    )
    assert candidate_status.status_code == 200, candidate_status.text
    status_payload = candidate_status.json()
    assert status_payload["recording"]["status"] == "deleted"
    assert status_payload["recording"]["downloadUrl"] is None
    assert status_payload["transcript"] is None


@pytest.mark.asyncio
async def test_delete_recording_forbidden_for_different_candidate(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-delete-auth@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="delete-owner@test.com",
        status="in_progress",
    )
    other_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="delete-other@test.com",
        status="in_progress",
    )
    recording = await _seed_uploaded_recording(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        filename="forbidden-same-company.mp4",
    )

    response = await async_client.post(
        f"/api/recordings/rec_{recording.id}/delete",
        headers=candidate_header_factory(other_session),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_recording_forbidden_for_recruiter_token(
    async_client,
    async_session,
    candidate_header_factory,
):
    recruiter = await create_recruiter(
        async_session, email="privacy-delete-recruiter@test.com"
    )
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    task = _handoff_task(tasks)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="delete-owner-recruiter@test.com",
        status="in_progress",
    )
    recording = await _seed_uploaded_recording(
        async_session,
        candidate_session=owner_session,
        task_id=task.id,
        filename="forbidden-recruiter.mp4",
    )

    response = await async_client.post(
        f"/api/recordings/rec_{recording.id}/delete",
        headers=candidate_header_factory(
            owner_session,
            token=f"recruiter:{recruiter.email}",
        ),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Candidate access required"


@pytest.mark.asyncio
async def test_delete_recording_forbidden_for_cross_company_candidate(
    async_client,
    async_session,
    candidate_header_factory,
):
    company_a = await create_company(async_session, name="Delete Co A")
    company_b = await create_company(async_session, name="Delete Co B")
    recruiter_a = await create_recruiter(
        async_session,
        email="privacy-delete-company-a@test.com",
        company=company_a,
    )
    recruiter_b = await create_recruiter(
        async_session,
        email="privacy-delete-company-b@test.com",
        company=company_b,
    )
    sim_a, tasks_a = await create_simulation(async_session, created_by=recruiter_a)
    sim_b, _tasks_b = await create_simulation(async_session, created_by=recruiter_b)
    task_a = _handoff_task(tasks_a)
    owner_session = await create_candidate_session(
        async_session,
        simulation=sim_a,
        invite_email="delete-cross-owner@test.com",
        status="in_progress",
    )
    other_company_session = await create_candidate_session(
        async_session,
        simulation=sim_b,
        invite_email="delete-cross-other@test.com",
        status="in_progress",
    )
    recording = await _seed_uploaded_recording(
        async_session,
        candidate_session=owner_session,
        task_id=task_a.id,
        filename="forbidden-cross-company.mp4",
    )

    response = await async_client.post(
        f"/api/recordings/rec_{recording.id}/delete",
        headers=candidate_header_factory(other_company_session),
    )

    assert response.status_code == 403
