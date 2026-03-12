from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains import FitProfile, Job, Submission, Task
from app.jobs import worker
from app.jobs.handlers.evaluation_run import handle_evaluation_run
from app.repositories.candidate_sessions import repository as cs_repo
from app.repositories.evaluations import repository as evaluation_repo
from app.repositories.evaluations.models import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
from app.repositories.jobs.models import JOB_STATUS_DEAD_LETTER
from app.repositories.recordings import repository as recordings_repo
from app.repositories.recordings.models import RECORDING_ASSET_STATUS_READY
from app.repositories.transcripts import repository as transcripts_repo
from app.repositories.transcripts.models import TRANSCRIPT_STATUS_READY
from app.services.evaluations.fit_profile_jobs import EVALUATION_RUN_JOB_TYPE
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


async def _seed_completed_candidate_session(
    async_session: AsyncSession,
    *,
    ai_eval_enabled_by_day: dict[str, bool] | None = None,
):
    recruiter = await create_recruiter(
        async_session,
        email="fit-profile-owner@test.com",
    )
    simulation, tasks = await create_simulation(
        async_session,
        created_by=recruiter,
        ai_eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        candidate_name="Fit Profile Candidate",
        invite_email="fit-profile-candidate@example.com",
    )
    tasks_by_day = {task.day_index: task for task in tasks}

    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[1],
        content_text="System design plan with tradeoffs, constraints, and rollout notes.",
        content_json={"kind": "day1_design", "sections": {"overview": "plan"}},
    )

    day2_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[2],
        content_text=None,
        code_repo_path="acme/fit-profile-repo",
        commit_sha="mutable-day2-sha",
        workflow_run_id="2002",
        diff_summary_json=json.dumps({"base": "base-day2", "head": "head-day2"}),
        tests_passed=5,
        tests_failed=1,
        test_output=json.dumps({"passed": 5, "failed": 1, "total": 6}),
    )
    day2_submission.checkpoint_sha = "mutable-day2-checkpoint"

    day3_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[3],
        content_text=None,
        code_repo_path="acme/fit-profile-repo",
        commit_sha="mutable-day3-sha",
        workflow_run_id="3003",
        diff_summary_json=json.dumps({"base": "base-day3", "head": "head-day3"}),
        tests_passed=6,
        tests_failed=0,
        test_output=json.dumps({"passed": 6, "failed": 0, "total": 6}),
    )
    day3_submission.final_sha = "mutable-day3-final"

    recording = await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks_by_day[4].id,
        storage_key=f"candidate-sessions/{candidate_session.id}/task4/video.webm",
        content_type="video/webm",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_READY,
        commit=False,
    )
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[4],
        content_text="handoff summary",
        recording_id=recording.id,
    )
    await transcripts_repo.create_transcript(
        async_session,
        recording_id=recording.id,
        status=TRANSCRIPT_STATUS_READY,
        text="I refactored the service layer and added tests.",
        segments_json=[
            {"startMs": 100, "endMs": 1200, "text": "I refactored the service layer."},
            {"startMs": 1300, "endMs": 2600, "text": "I added regression tests."},
        ],
        model_name="whisper-test",
        commit=False,
    )

    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[5],
        content_text="Reflection on constraints and communication.",
        content_json={"kind": "day5_reflection", "sections": {"reflection": "done"}},
    )

    cutoff_at = datetime.now(UTC).replace(microsecond=0)
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="cutoff-day2-fixed",
        eval_basis_ref="refs/heads/main@cutoff:day2",
        commit=False,
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=3,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="cutoff-day3-fixed",
        eval_basis_ref="refs/heads/main@cutoff:day3",
        commit=False,
    )

    await async_session.commit()
    return recruiter, candidate_session


async def _run_worker_once(async_session: AsyncSession, *, worker_id: str) -> bool:
    session_maker = async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        return await worker.run_once(
            session_maker=session_maker,
            worker_id=worker_id,
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()


@pytest.mark.asyncio
async def test_generate_fit_profile_returns_queued_and_get_running(
    async_client,
    async_session,
    auth_header_factory,
):
    recruiter, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    before_generate = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile",
        headers=auth_header_factory(recruiter),
    )
    assert before_generate.status_code == 200, before_generate.text
    assert before_generate.json() == {"status": "not_started"}

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(recruiter),
    )
    assert generate.status_code == 202, generate.text
    body = generate.json()
    assert body["status"] == "queued"
    assert isinstance(body["jobId"], str)

    job = await async_session.get(Job, body["jobId"])
    assert job is not None
    assert job.job_type == EVALUATION_RUN_JOB_TYPE
    assert job.candidate_session_id == candidate_session.id

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile",
        headers=auth_header_factory(recruiter),
    )
    assert fetch.status_code == 200, fetch.text
    assert fetch.json() == {"status": "running"}


@pytest.mark.asyncio
async def test_fit_profile_worker_completion_returns_ready_and_evidence(
    async_client,
    async_session,
    auth_header_factory,
):
    recruiter, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(recruiter),
    )
    assert generate.status_code == 202, generate.text

    handled = await _run_worker_once(
        async_session, worker_id="fit-profile-worker-ready"
    )
    assert handled is True

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile",
        headers=auth_header_factory(recruiter),
    )
    assert fetch.status_code == 200, fetch.text
    payload = fetch.json()
    assert payload["status"] == "ready"
    assert payload["generatedAt"] is not None
    report = payload["report"]
    assert isinstance(report["overallFitScore"], float)
    assert report["recommendation"] in {"hire", "strong_hire", "no_hire", "lean_hire"}
    assert isinstance(report["confidence"], float)
    assert isinstance(report["dayScores"], list)
    assert isinstance(report["version"], dict)

    evidence_items = [
        evidence for day in report["dayScores"] for evidence in day.get("evidence", [])
    ]
    kinds = {item.get("kind") for item in evidence_items}
    assert "commit" in kinds
    assert "diff" in kinds
    assert "test" in kinds
    assert "transcript" in kinds
    assert "reflection" in kinds

    for item in evidence_items:
        if item.get("kind") == "transcript":
            assert isinstance(item.get("startMs"), int)
            assert isinstance(item.get("endMs"), int)
            assert item["endMs"] >= item["startMs"]
        if item.get("kind") == "commit":
            assert isinstance(item.get("ref"), str)
            assert item.get("url", "").startswith("https://")

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 1
    run = runs[0]
    assert run.status == EVALUATION_RUN_STATUS_COMPLETED
    assert run.basis_fingerprint is not None
    assert run.generated_at is not None
    assert run.job_id is not None
    assert run.day2_checkpoint_sha == "cutoff-day2-fixed"
    assert run.day3_final_sha == "cutoff-day3-fixed"

    marker = (
        await async_session.execute(
            select(FitProfile).where(
                FitProfile.candidate_session_id == candidate_session.id
            )
        )
    ).scalar_one_or_none()
    assert marker is not None
    assert marker.generated_at is not None


@pytest.mark.asyncio
async def test_fit_profile_auth_404_and_403(
    async_client,
    async_session,
    auth_header_factory,
):
    owner, candidate_session = await _seed_completed_candidate_session(async_session)
    outsider = await create_recruiter(
        async_session,
        email="fit-profile-outsider@test.com",
    )
    await async_session.commit()

    missing_post = await async_client.post(
        "/api/candidate_sessions/999999/fit_profile/generate",
        headers=auth_header_factory(owner),
    )
    assert missing_post.status_code == 404

    missing_get = await async_client.get(
        "/api/candidate_sessions/999999/fit_profile",
        headers=auth_header_factory(owner),
    )
    assert missing_get.status_code == 404

    forbidden_post = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(outsider),
    )
    assert forbidden_post.status_code == 403

    forbidden_get = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile",
        headers=auth_header_factory(outsider),
    )
    assert forbidden_get.status_code == 403


@pytest.mark.asyncio
async def test_fit_profile_disabled_day_multiple_runs_and_cutoff_immutability(
    async_client,
    async_session,
    auth_header_factory,
):
    recruiter, candidate_session = await _seed_completed_candidate_session(
        async_session,
        ai_eval_enabled_by_day={"4": False},
    )

    first_generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(recruiter),
    )
    assert first_generate.status_code == 202, first_generate.text
    assert (
        await _run_worker_once(async_session, worker_id="fit-profile-worker-first")
        is True
    )

    day2_submission = (
        await async_session.execute(
            select(Submission)
            .join(Task, Task.id == Submission.task_id)
            .where(
                Submission.candidate_session_id == candidate_session.id,
                Task.day_index == 2,
            )
        )
    ).scalar_one()
    day2_submission.commit_sha = "mutated-latest-day2-sha"
    day2_submission.checkpoint_sha = "mutated-latest-day2-checkpoint"
    await async_session.commit()

    second_generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(recruiter),
    )
    assert second_generate.status_code == 202, second_generate.text
    assert (
        await _run_worker_once(async_session, worker_id="fit-profile-worker-second")
        is True
    )

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 2
    assert runs[0].id != runs[1].id

    for run in runs:
        assert run.day2_checkpoint_sha == "cutoff-day2-fixed"
        assert run.day3_final_sha == "cutoff-day3-fixed"
        assert run.status == EVALUATION_RUN_STATUS_COMPLETED
        assert run.metadata_json is not None
        assert run.metadata_json.get("disabledDayIndexes") == [4]
        assert 4 not in [row.day_index for row in run.day_scores]

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile",
        headers=auth_header_factory(recruiter),
    )
    assert fetch.status_code == 200, fetch.text
    body = fetch.json()
    assert body["status"] == "ready"
    day_scores = body["report"]["dayScores"]
    day4_entry = next(day for day in day_scores if day["dayIndex"] == 4)
    assert day4_entry["status"] == "human_review_required"
    assert day4_entry["reason"] == "ai_eval_disabled_for_day"
    assert day4_entry["score"] is None
    scored_days = [day for day in day_scores if day["status"] == "scored"]
    assert scored_days
    expected_overall = round(
        sum(float(day["score"]) for day in scored_days) / len(scored_days),
        4,
    )
    assert body["report"]["overallFitScore"] == expected_overall


@pytest.mark.asyncio
async def test_fit_profile_failure_surface_when_latest_run_failed(
    async_client,
    async_session,
    auth_header_factory,
    monkeypatch,
):
    recruiter, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    class _FailingEvaluator:
        async def evaluate(self, _bundle):
            raise RuntimeError("forced evaluator failure")

    monkeypatch.setattr(
        "app.services.evaluations.fit_profile_pipeline.evaluator_service.get_fit_profile_evaluator",
        lambda: _FailingEvaluator(),
    )

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(recruiter),
    )
    assert generate.status_code == 202, generate.text
    generated_job_id = generate.json()["jobId"]

    handled = await _run_worker_once(
        async_session, worker_id="fit-profile-worker-failed"
    )
    assert handled is True

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 1
    assert runs[0].status == EVALUATION_RUN_STATUS_FAILED
    assert runs[0].error_code == "evaluation_failed"
    assert runs[0].job_id == generated_job_id

    durable_job = await async_session.get(Job, generated_job_id)
    assert durable_job is not None
    assert durable_job.status == JOB_STATUS_DEAD_LETTER

    marker = (
        await async_session.execute(
            select(FitProfile).where(
                FitProfile.candidate_session_id == candidate_session.id
            )
        )
    ).scalar_one_or_none()
    assert marker is None

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile",
        headers=auth_header_factory(recruiter),
    )
    assert fetch.status_code == 200, fetch.text
    assert fetch.json() == {"status": "failed", "errorCode": "evaluation_failed"}


@pytest.mark.asyncio
async def test_fit_profile_same_job_reexecution_is_idempotent(
    async_client,
    async_session,
    auth_header_factory,
):
    recruiter, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/fit_profile/generate",
        headers=auth_header_factory(recruiter),
    )
    assert generate.status_code == 202, generate.text
    job_id = generate.json()["jobId"]

    job = await async_session.get(Job, job_id)
    assert job is not None
    payload = dict(job.payload_json)

    first = await handle_evaluation_run(payload)
    second = await handle_evaluation_run(payload)

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert first["evaluationRunId"] == second["evaluationRunId"]

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 1
    assert runs[0].job_id == job_id
