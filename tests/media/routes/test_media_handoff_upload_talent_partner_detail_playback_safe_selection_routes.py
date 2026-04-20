from __future__ import annotations

import pytest

from app.submissions.repositories import repository as submissions_repo
from tests.media.routes.media_handoff_upload_api_utils import *


async def _complete_valid_recording(
    async_client,
    async_session,
    *,
    candidate_session,
    task,
    candidate_header_factory,
    filename: str,
    size_bytes: int,
):
    headers = candidate_header_factory(candidate_session)
    init_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/init",
        headers=headers,
        json={
            "contentType": "video/mp4",
            "sizeBytes": size_bytes,
            "filename": filename,
            "durationSeconds": 600,
        },
    )
    assert init_response.status_code == 200, init_response.text
    recording = (
        await async_session.execute(
            select(RecordingAsset)
            .where(
                RecordingAsset.candidate_session_id == candidate_session.id,
                RecordingAsset.task_id == task.id,
                RecordingAsset.asset_kind == "recording",
            )
            .order_by(RecordingAsset.id.desc())
            .limit(1)
        )
    ).scalar_one()
    _fake_storage_provider().set_object_metadata(
        recording.storage_key,
        content_type=recording.content_type,
        size_bytes=recording.bytes,
        duration_seconds=600,
    )
    complete_response = await async_client.post(
        f"/api/tasks/{task.id}/handoff/upload/complete",
        headers=headers,
        json={"recordingId": init_response.json()["recordingId"]},
    )
    assert complete_response.status_code == 200, complete_response.text
    return recording


@pytest.mark.asyncio
@pytest.mark.parametrize("new_status", ["failed", "deleted", "purged"])
async def test_talent_partner_detail_keeps_prior_valid_recording_when_newer_invalid_recording_exists(
    async_client,
    async_session,
    candidate_header_factory,
    new_status,
):
    talent_partner = await create_talent_partner(
        async_session, email=f"handoff-detail-{new_status}@test.com"
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

    first_recording = await _complete_valid_recording(
        async_client,
        async_session,
        candidate_session=candidate_session,
        task=task,
        candidate_header_factory=candidate_header_factory,
        filename="first.mp4",
        size_bytes=4_096,
    )
    await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            f"recordings/{new_status}.mp4"
        ),
        content_type="video/mp4",
        bytes_count=8_192,
        status=new_status,
        commit=True,
    )

    submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert submission is not None
    submission.recording_id = first_recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{first_recording.id}"
    assert body["handoff"]["recordingId"] == f"rec_{first_recording.id}"


@pytest.mark.asyncio
async def test_talent_partner_detail_ignores_newer_supplemental_asset(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-detail-supplemental@test.com"
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

    first_recording = await _complete_valid_recording(
        async_client,
        async_session,
        candidate_session=candidate_session,
        task=task,
        candidate_header_factory=candidate_header_factory,
        filename="first.mp4",
        size_bytes=4_096,
    )
    await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "supplemental/slides.pdf"
        ),
        content_type="application/pdf",
        bytes_count=1_024,
        asset_kind="supplemental",
        status="uploaded",
        commit=True,
    )

    submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert submission is not None
    submission.recording_id = first_recording.id
    await async_session.commit()

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{first_recording.id}"
    assert body["handoff"]["recordingId"] == f"rec_{first_recording.id}"


@pytest.mark.asyncio
async def test_talent_partner_detail_switches_to_newer_valid_resubmission(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-detail-resubmit@test.com"
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

    await _complete_valid_recording(
        async_client,
        async_session,
        candidate_session=candidate_session,
        task=task,
        candidate_header_factory=candidate_header_factory,
        filename="first.mp4",
        size_bytes=4_096,
    )
    second_recording = await _complete_valid_recording(
        async_client,
        async_session,
        candidate_session=candidate_session,
        task=task,
        candidate_header_factory=candidate_header_factory,
        filename="second.mp4",
        size_bytes=8_192,
    )

    submission = await submissions_repo.get_by_candidate_session_task(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
    )
    assert submission is not None
    assert submission.recording_id == second_recording.id

    response = await async_client.get(
        f"/api/submissions/{submission.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recording"]["recordingId"] == f"rec_{second_recording.id}"
    assert body["handoff"]["recordingId"] == f"rec_{second_recording.id}"
