from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.media.repositories.recordings import (
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.media.repositories.recordings import (
    repository as recordings_repo,
)
from app.media.repositories.transcripts import (
    TRANSCRIPT_STATUS_READY,
)
from app.media.repositories.transcripts import (
    repository as transcripts_repo,
)
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


def _task(tasks, day_index: int):
    return next(task for task in tasks if task.day_index == day_index)


@pytest.mark.asyncio
async def test_candidate_session_review_returns_completed_artifacts(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="review-route@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    completed_at = datetime.now(UTC).replace(microsecond=0)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="completed",
        completed_at=completed_at,
        invite_email="review@example.com",
        candidate_email="review@example.com",
        with_default_schedule=True,
    )

    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=_task(tasks, 1),
        content_text="# Architecture\n\nFinal plan.",
        submitted_at=completed_at - timedelta(days=4),
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=_task(tasks, 2),
        content_text="Implemented the feature.",
        submitted_at=completed_at - timedelta(days=3),
        tests_passed=12,
        tests_failed=1,
        test_output="12 passed, 1 failed",
        code_repo_path="octocat/demo-sim",
        commit_sha="abc123",
        workflow_run_id="42",
        workflow_run_status="completed",
        workflow_run_conclusion="success",
        diff_summary_json='{"filesChanged": 2}',
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=completed_at - timedelta(days=3, hours=1),
        cutoff_commit_sha="abc123",
        eval_basis_ref="refs/heads/main",
        commit=False,
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=_task(tasks, 3),
        content_text="Fixed the failing tests.",
        submitted_at=completed_at - timedelta(days=2),
        tests_passed=8,
        tests_failed=0,
        test_output="8 passed",
        code_repo_path="octocat/demo-sim",
        commit_sha="def456",
        workflow_run_id="43",
        workflow_run_status="completed",
        workflow_run_conclusion="success",
        diff_summary_json='{"filesChanged": 1}',
    )
    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=_task(tasks, 4).id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{_task(tasks, 4).id}/"
            "recordings/review-demo.mp4"
        ),
        content_type="video/mp4",
        bytes_count=4_096,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=False,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="Walked through the completed demo.",
        segments_json=[
            {"startMs": 0, "endMs": 1400, "text": "Walked through the completed demo."}
        ],
        model_name="gpt-4o-transcribe",
        commit=False,
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=_task(tasks, 4),
        content_text="Presentation uploaded",
        submitted_at=completed_at - timedelta(days=1),
        recording_id=recording.id,
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=_task(tasks, 5),
        content_text="## Reflection\n\nWhat I would improve next.",
        submitted_at=completed_at,
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.token}/review",
        headers={"Authorization": "Bearer candidate:review@example.com"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidateSessionId"] == candidate_session.id
    assert body["status"] == "completed"
    assert len(body["artifacts"]) == 5

    artifacts = {artifact["dayIndex"]: artifact for artifact in body["artifacts"]}
    assert artifacts[1]["kind"] == "markdown"
    assert artifacts[1]["markdown"].startswith("# Architecture")
    assert artifacts[2]["kind"] == "workspace"
    assert artifacts[2]["repoFullName"] == "octocat/demo-sim"
    assert artifacts[2]["cutoffCommitSha"] == "abc123"
    assert artifacts[2]["testResults"]["passed"] == 12
    assert artifacts[4]["kind"] == "presentation"
    assert artifacts[4]["recording"]["status"] == RECORDING_ASSET_STATUS_UPLOADED
    assert artifacts[4]["recording"]["downloadUrl"] is not None
    assert artifacts[4]["transcript"]["status"] == TRANSCRIPT_STATUS_READY
    assert artifacts[4]["transcript"]["segments"][0]["text"].startswith(
        "Walked through"
    )
    assert artifacts[5]["kind"] == "markdown"
    assert "Reflection" in artifacts[5]["markdown"]


@pytest.mark.asyncio
async def test_candidate_session_review_rejects_incomplete_sessions(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="review-incomplete@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        invite_email="review-incomplete@example.com",
        candidate_email="review-incomplete@example.com",
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.token}/review",
        headers={"Authorization": "Bearer candidate:review-incomplete@example.com"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Trial is not complete yet"
