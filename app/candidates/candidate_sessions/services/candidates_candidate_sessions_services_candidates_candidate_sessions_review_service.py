"""Application module for candidates candidate sessions services candidates candidate sessions review service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_service import (
    fetch_by_token,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_ownership_service import (
    ensure_candidate_ownership,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_review_schema import (
    CandidateCompletedReviewResponse,
    CandidateReviewMarkdownArtifact,
    CandidateReviewPresentationArtifact,
    CandidateReviewWorkspaceArtifact,
)
from app.integrations.storage_media import (
    get_storage_media_provider,
    resolve_signed_url_ttl,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import repository as transcripts_repo
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import Submission, Task
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.submissions.presentation import present_detail


async def build_candidate_completed_review(
    db: AsyncSession,
    *,
    token: str,
    principal: Principal,
    now: datetime | None = None,
) -> CandidateCompletedReviewResponse:
    """Return candidate review payload for a completed session."""
    resolved_now = now or shared_utcnow()
    candidate_session = await fetch_by_token(db, token, now=resolved_now)
    changed = ensure_candidate_ownership(candidate_session, principal, now=resolved_now)
    if changed:
        await db.commit()
        await db.refresh(
            candidate_session, attribute_names=["trial", "scenario_version"]
        )

    if (
        candidate_session.completed_at is None
        and candidate_session.status != "completed"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial is not complete yet",
        )

    tasks = await _load_tasks(db, trial_id=candidate_session.trial_id)
    submissions = await _load_submissions(
        db,
        candidate_session_id=candidate_session.id,
        task_ids=[task.id for task in tasks],
    )
    day_audits = {
        audit.day_index: audit
        for audit in await cs_repo.list_day_audits(
            db,
            candidate_session_ids=[candidate_session.id],
            day_indexes=[task.day_index for task in tasks],
        )
    }
    artifacts = []
    for task in tasks:
        submission = submissions.get(task.id)
        if submission is None:
            continue
        recording = transcript = recording_download_url = None
        if (task.type or "").lower() == "handoff":
            (
                recording,
                transcript,
                recording_download_url,
            ) = await _resolve_candidate_media(
                db,
                candidate_session_id=candidate_session.id,
                task_id=task.id,
            )
        payload = present_detail(
            submission,
            task,
            candidate_session,
            candidate_session.trial,
            day_audit=day_audits.get(task.day_index),
            recording=recording,
            transcript=transcript,
            recording_download_url=recording_download_url,
        )
        artifacts.append(_build_artifact(task=task, payload=payload))

    completed_at = candidate_session.completed_at or resolved_now
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)

    return CandidateCompletedReviewResponse(
        candidateSessionId=candidate_session.id,
        status=candidate_session.status,
        completedAt=completed_at,
        trial={
            "id": candidate_session.trial.id,
            "title": candidate_session.trial.title,
            "role": candidate_session.trial.role,
        },
        candidateTimezone=getattr(candidate_session, "candidate_timezone", None),
        dayWindows=(getattr(candidate_session, "day_windows_json", None) or []),
        artifacts=artifacts,
    )


async def _load_tasks(db: AsyncSession, *, trial_id: int) -> list[Task]:
    stmt = (
        select(Task)
        .where(Task.trial_id == trial_id)
        .order_by(Task.day_index.asc(), Task.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _load_submissions(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_ids: list[int],
) -> dict[int, Submission]:
    if not task_ids:
        return {}
    stmt = (
        select(Submission)
        .where(
            Submission.candidate_session_id == candidate_session_id,
            Submission.task_id.in_(task_ids),
        )
        .order_by(Submission.task_id.asc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return {submission.task_id: submission for submission in rows}


async def _resolve_candidate_media(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    task_id: int,
):
    recording = await recordings_repo.get_latest_for_task_session(
        db,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
    )
    if recording is None or recordings_repo.is_deleted_or_purged(recording):
        return None, None, None
    transcript = await transcripts_repo.get_by_recording_id(db, recording.id)
    if not recordings_repo.is_downloadable(recording):
        return recording, transcript, None
    storage_provider = get_storage_media_provider()
    download_url = storage_provider.create_signed_download_url(
        recording.storage_key,
        expires_seconds=resolve_signed_url_ttl(),
    )
    return recording, transcript, download_url


def _build_artifact(*, task: Task, payload: dict[str, object]):
    task_type = str(getattr(task, "type", "") or "")
    common = {
        "dayIndex": int(task.day_index),
        "taskId": int(task.id),
        "taskType": task_type,
        "title": str(getattr(task, "title", "") or f"Day {task.day_index}"),
        "submittedAt": payload["submittedAt"],
    }
    if int(task.day_index) in {1, 5}:
        return CandidateReviewMarkdownArtifact(
            kind="markdown",
            markdown=payload.get("contentText"),
            contentJson=payload.get("contentJson"),
            **common,
        )
    if int(task.day_index) in {2, 3}:
        code = payload.get("code") or {}
        return CandidateReviewWorkspaceArtifact(
            kind="workspace",
            repoFullName=getattr(code, "get", lambda *_: None)("repoFullName"),
            commitSha=payload.get("commitSha"),
            cutoffCommitSha=payload.get("cutoffCommitSha"),
            cutoffAt=payload.get("cutoffAt"),
            workflowUrl=payload.get("workflowUrl"),
            commitUrl=payload.get("commitUrl"),
            diffUrl=payload.get("diffUrl"),
            diffSummary=payload.get("diffSummary"),
            testResults=payload.get("testResults"),
            **common,
        )
    return CandidateReviewPresentationArtifact(
        kind="presentation",
        recording=payload.get("recording"),
        transcript=payload.get("transcript"),
        **common,
    )


__all__ = ["build_candidate_completed_review"]
