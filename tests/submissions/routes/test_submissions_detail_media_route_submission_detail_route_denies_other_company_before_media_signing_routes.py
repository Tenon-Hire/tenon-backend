from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_detail_media_routes_utils import *


@pytest.mark.asyncio
async def test_submission_detail_route_denies_other_company_before_media_signing(
    async_session,
    monkeypatch,
):
    owner_company = await create_company(async_session, name="Owner Co")
    other_company = await create_company(async_session, name="Other Co")
    owner = await create_talent_partner(
        async_session,
        email="detail-route-owner@test.com",
        company=owner_company,
    )
    outsider = await create_talent_partner(
        async_session,
        email="detail-route-outsider@test.com",
        company=other_company,
    )
    sim, tasks = await create_trial(async_session, created_by=owner)
    task = _handoff_task(tasks)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=task,
        content_text="handoff notes",
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task.id}/"
            "recordings/forbidden.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="sensitive transcript",
        model_name="test-model",
        commit=True,
    )
    submission.recording_id = recording.id
    await async_session.commit()

    calls = {"signed_download": 0}

    class _TrackingProvider:
        def create_signed_download_url(self, key: str, expires_seconds: int) -> str:
            del key, expires_seconds
            calls["signed_download"] += 1
            return "https://fake-storage.local/download?never=true"

    monkeypatch.setattr(detail_route, "get_storage_media_provider", _TrackingProvider)

    with pytest.raises(HTTPException) as exc_info:
        await detail_route.get_submission_detail_route(
            submission_id=submission.id,
            db=async_session,
            user=outsider,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Submission access forbidden"
    assert calls["signed_download"] == 0
