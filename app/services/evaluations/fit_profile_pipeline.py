from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker
from app.domains import CandidateDayAudit, RecordingAsset, Submission, Task, Transcript
from app.domains.candidate_sessions import repository as cs_repo
from app.repositories.evaluations import repository as evaluation_repo
from app.repositories.evaluations.models import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
)
from app.repositories.recordings import repository as recordings_repo
from app.repositories.submissions import fit_profile_repository
from app.services.evaluations import evaluator as evaluator_service
from app.services.evaluations import runs as evaluation_runs
from app.services.evaluations.fit_profile_access import (
    get_candidate_session_evaluation_context,
    has_company_access,
)

logger = logging.getLogger(__name__)

DEFAULT_EVALUATION_MODEL_NAME = "tenon-fit-evaluator"
DEFAULT_EVALUATION_MODEL_VERSION = "2026-03-12"
DEFAULT_EVALUATION_PROMPT_VERSION = "fit-profile-v1"
DEFAULT_RUBRIC_VERSION = "rubric-v1"


def _parse_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _normalize_day_toggles(raw: Any) -> tuple[list[int], list[int]]:
    disabled: list[int] = []
    enabled: list[int] = []
    toggles = raw if isinstance(raw, dict) else {}
    for day in range(1, 6):
        if toggles.get(str(day)) is False:
            disabled.append(day)
        else:
            enabled.append(day)
    return enabled, disabled


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _parse_diff_summary(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(value, dict):
        return None
    return value


def _segment_text(segment: dict[str, Any]) -> str | None:
    for key in ("text", "content", "excerpt"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _segment_start_ms(segment: dict[str, Any]) -> int | None:
    for key in ("startMs", "start_ms", "start"):
        value = _safe_int(segment.get(key))
        if value is not None:
            return max(0, value)
    return None


def _segment_end_ms(segment: dict[str, Any]) -> int | None:
    for key in ("endMs", "end_ms", "end"):
        value = _safe_int(segment.get(key))
        if value is not None:
            return max(0, value)
    return None


def _normalize_transcript_segments(raw_segments: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_segments, list):
        return []
    normalized: list[dict[str, Any]] = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            continue
        start_ms = _segment_start_ms(raw_segment)
        end_ms = _segment_end_ms(raw_segment)
        if start_ms is None or end_ms is None:
            continue
        if end_ms < start_ms:
            end_ms = start_ms
        text = _segment_text(raw_segment)
        segment: dict[str, Any] = {
            "startMs": start_ms,
            "endMs": end_ms,
        }
        if text is not None:
            segment["text"] = text
        normalized.append(segment)
    return normalized


def _submission_basis_hash(submission: Submission | None) -> str | None:
    if submission is None:
        return None
    submission_basis = {
        "id": submission.id,
        "submittedAt": submission.submitted_at.isoformat()
        if submission.submitted_at
        else None,
        "contentText": submission.content_text,
        "contentJson": submission.content_json,
        "commitSha": submission.commit_sha,
        "checkpointSha": submission.checkpoint_sha,
        "finalSha": submission.final_sha,
        "workflowRunId": submission.workflow_run_id,
        "diffSummaryJson": submission.diff_summary_json,
        "testsPassed": submission.tests_passed,
        "testsFailed": submission.tests_failed,
        "testOutput": submission.test_output,
        "lastRunAt": submission.last_run_at.isoformat()
        if submission.last_run_at
        else None,
    }
    return _stable_hash(submission_basis)


def _transcript_basis_hash(transcript: Transcript | None) -> str | None:
    if transcript is None:
        return None
    transcript_basis = {
        "id": transcript.id,
        "status": transcript.status,
        "modelName": transcript.model_name,
        "text": transcript.text,
        "segments": transcript.segments_json,
    }
    return _stable_hash(transcript_basis)


async def _submissions_by_day(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    simulation_id: int,
) -> dict[int, Submission]:
    rows = (
        await db.execute(
            select(Submission, Task)
            .join(Task, Task.id == Submission.task_id)
            .where(
                Submission.candidate_session_id == candidate_session_id,
                Task.simulation_id == simulation_id,
            )
            .order_by(Task.day_index.asc())
        )
    ).all()
    by_day: dict[int, Submission] = {}
    for submission, task in rows:
        by_day[task.day_index] = submission
    return by_day


async def _tasks_by_day(db: AsyncSession, *, simulation_id: int) -> dict[int, Task]:
    tasks = (
        (
            await db.execute(
                select(Task)
                .where(Task.simulation_id == simulation_id)
                .order_by(Task.day_index.asc(), Task.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return {task.day_index: task for task in tasks}


async def _day_audits_by_day(
    db: AsyncSession,
    *,
    candidate_session_id: int,
) -> dict[int, CandidateDayAudit]:
    rows = await cs_repo.list_day_audits(
        db,
        candidate_session_ids=[candidate_session_id],
        day_indexes=[2, 3],
    )
    return {row.day_index: row for row in rows}


async def _resolve_day4_transcript(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    day4_task: Task | None,
    day4_submission: Submission | None,
) -> tuple[Transcript | None, str]:
    recording: RecordingAsset | None = None
    if day4_submission is not None and isinstance(day4_submission.recording_id, int):
        recording = await db.get(RecordingAsset, day4_submission.recording_id)
        if recordings_repo.is_deleted_or_purged(recording):
            recording = None

    if recording is None and day4_task is not None:
        recording = (
            await db.execute(
                select(RecordingAsset)
                .where(
                    RecordingAsset.candidate_session_id == candidate_session_id,
                    RecordingAsset.task_id == day4_task.id,
                )
                .order_by(RecordingAsset.created_at.desc(), RecordingAsset.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if recordings_repo.is_deleted_or_purged(recording):
            recording = None

    if recording is None:
        return None, "transcript:missing"

    transcript = (
        await db.execute(
            select(Transcript).where(
                Transcript.recording_id == recording.id,
                Transcript.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if transcript is None:
        return None, f"transcript:recording:{recording.id}:missing"
    return transcript, f"transcript:{transcript.id}"


def _build_basis_references(
    *,
    scenario_version_id: int,
    scenario_rubric_version: str,
    day_audits: dict[int, CandidateDayAudit],
    submissions_by_day: dict[int, Submission],
    transcript_reference: str,
    transcript_hash: str | None,
    disabled_day_indexes: list[int],
) -> dict[str, Any]:
    day_refs: dict[str, Any] = {}
    for day_index in range(1, 6):
        submission = submissions_by_day.get(day_index)
        day_audit = day_audits.get(day_index)
        day_refs[str(day_index)] = {
            "submissionId": submission.id if submission is not None else None,
            "submissionBasisHash": _submission_basis_hash(submission),
            "cutoffCommitSha": (
                day_audit.cutoff_commit_sha if day_audit is not None else None
            ),
            "evalBasisRef": day_audit.eval_basis_ref if day_audit is not None else None,
        }

    return {
        "scenarioVersionId": scenario_version_id,
        "rubricVersion": scenario_rubric_version,
        "dayRefs": day_refs,
        "transcriptReference": transcript_reference,
        "transcriptBasisHash": transcript_hash,
        "disabledDayIndexes": disabled_day_indexes,
    }


async def process_evaluation_run_job(payload_json: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    candidate_session_id = _parse_positive_int(payload_json.get("candidateSessionId"))
    payload_company_id = _parse_positive_int(payload_json.get("companyId"))
    requested_by_user_id = _parse_positive_int(payload_json.get("requestedByUserId"))
    job_id = (
        payload_json.get("jobId")
        if isinstance(payload_json.get("jobId"), str)
        else None
    )

    if candidate_session_id is None or payload_company_id is None:
        return {
            "status": "skipped_invalid_payload",
            "candidateSessionId": candidate_session_id,
            "companyId": payload_company_id,
        }

    logger.info(
        "evaluation_generation_started candidateSessionId=%s companyId=%s jobId=%s",
        candidate_session_id,
        payload_company_id,
        job_id,
    )

    async with async_session_maker() as db:
        context = await get_candidate_session_evaluation_context(
            db,
            candidate_session_id=candidate_session_id,
        )
        if context is None:
            return {
                "status": "candidate_session_not_found",
                "candidateSessionId": candidate_session_id,
            }
        if not has_company_access(
            simulation_company_id=context.simulation.company_id,
            expected_company_id=payload_company_id,
        ):
            return {
                "status": "company_access_forbidden",
                "candidateSessionId": candidate_session_id,
            }

        enabled_days, disabled_days = _normalize_day_toggles(
            context.simulation.ai_eval_enabled_by_day
        )

        tasks_by_day = await _tasks_by_day(db, simulation_id=context.simulation.id)
        submissions_by_day = await _submissions_by_day(
            db,
            candidate_session_id=context.candidate_session.id,
            simulation_id=context.simulation.id,
        )
        day_audits = await _day_audits_by_day(
            db,
            candidate_session_id=context.candidate_session.id,
        )

        day4_task = tasks_by_day.get(4)
        day4_submission = submissions_by_day.get(4)
        transcript, transcript_reference = await _resolve_day4_transcript(
            db,
            candidate_session_id=context.candidate_session.id,
            day4_task=day4_task,
            day4_submission=day4_submission,
        )
        normalized_segments = _normalize_transcript_segments(
            transcript.segments_json if transcript is not None else None
        )

        scenario_rubric_version = (
            context.scenario_version.rubric_version
            if context.scenario_version is not None
            and isinstance(context.scenario_version.rubric_version, str)
            and context.scenario_version.rubric_version.strip()
            else DEFAULT_RUBRIC_VERSION
        )

        day_inputs: list[evaluator_service.DayEvaluationInput] = []
        for day_index in range(1, 6):
            task = tasks_by_day.get(day_index)
            submission = submissions_by_day.get(day_index)
            day_audit = day_audits.get(day_index)
            day_inputs.append(
                evaluator_service.DayEvaluationInput(
                    day_index=day_index,
                    task_id=task.id if task is not None else None,
                    task_type=task.type if task is not None else None,
                    submission_id=submission.id if submission is not None else None,
                    content_text=submission.content_text
                    if submission is not None
                    else None,
                    content_json=(
                        submission.content_json
                        if submission is not None
                        and isinstance(submission.content_json, dict)
                        else None
                    ),
                    repo_full_name=(
                        submission.code_repo_path if submission is not None else None
                    ),
                    commit_sha=(
                        submission.commit_sha if submission is not None else None
                    ),
                    workflow_run_id=(
                        submission.workflow_run_id if submission is not None else None
                    ),
                    diff_summary=(
                        _parse_diff_summary(submission.diff_summary_json)
                        if submission is not None
                        else None
                    ),
                    tests_passed=(
                        submission.tests_passed if submission is not None else None
                    ),
                    tests_failed=(
                        submission.tests_failed if submission is not None else None
                    ),
                    transcript_reference=transcript_reference
                    if day_index == 4
                    else None,
                    transcript_segments=normalized_segments if day_index == 4 else [],
                    cutoff_commit_sha=(
                        day_audit.cutoff_commit_sha if day_audit is not None else None
                    ),
                    eval_basis_ref=(
                        day_audit.eval_basis_ref if day_audit is not None else None
                    ),
                )
            )

        basis_refs = _build_basis_references(
            scenario_version_id=context.candidate_session.scenario_version_id,
            scenario_rubric_version=scenario_rubric_version,
            day_audits=day_audits,
            submissions_by_day=submissions_by_day,
            transcript_reference=transcript_reference,
            transcript_hash=_transcript_basis_hash(transcript),
            disabled_day_indexes=disabled_days,
        )
        basis_fingerprint = _stable_hash(
            {
                "candidateSessionId": context.candidate_session.id,
                "simulationId": context.simulation.id,
                "scenarioVersionId": context.candidate_session.scenario_version_id,
                "basis": basis_refs,
            }
        )

        day2_submission = submissions_by_day.get(2)
        day3_submission = submissions_by_day.get(3)
        day2_checkpoint_sha = (
            (
                day_audits.get(2).cutoff_commit_sha
                if day_audits.get(2) is not None
                else None
            )
            or (day2_submission.checkpoint_sha if day2_submission is not None else None)
            or (day2_submission.commit_sha if day2_submission is not None else None)
            or "day2-missing"
        )
        day3_final_sha = (
            (
                day_audits.get(3).cutoff_commit_sha
                if day_audits.get(3) is not None
                else None
            )
            or (day3_submission.final_sha if day3_submission is not None else None)
            or (day3_submission.commit_sha if day3_submission is not None else None)
            or "day3-missing"
        )
        cutoff_commit_sha = (
            day3_final_sha if day3_final_sha != "day3-missing" else day2_checkpoint_sha
        )

        run_metadata = {
            "jobId": job_id,
            "basisFingerprint": basis_fingerprint,
            "disabledDayIndexes": disabled_days,
            "enabledDayIndexes": enabled_days,
            "basisRefs": basis_refs,
            "requestedByUserId": requested_by_user_id,
        }

        existing_run = None
        if job_id is not None:
            existing_run = await evaluation_repo.get_run_by_job_id(
                db,
                job_id=job_id,
                candidate_session_id=context.candidate_session.id,
                for_update=True,
            )

        if existing_run is not None:
            run = existing_run
            if run.status == EVALUATION_RUN_STATUS_COMPLETED:
                duration_ms = int((perf_counter() - started) * 1000)
                logger.info(
                    "evaluation_generation_completed candidateSessionId=%s runId=%s jobId=%s durationMs=%s modelVersion=%s promptVersion=%s rubricVersion=%s basisFingerprint=%s",
                    context.candidate_session.id,
                    run.id,
                    job_id,
                    duration_ms,
                    run.model_version,
                    run.prompt_version,
                    run.rubric_version,
                    run.basis_fingerprint,
                )
                return {
                    "status": "completed",
                    "candidateSessionId": context.candidate_session.id,
                    "evaluationRunId": run.id,
                    "basisFingerprint": run.basis_fingerprint,
                    "durationMs": duration_ms,
                    "modelVersion": run.model_version,
                    "promptVersion": run.prompt_version,
                    "rubricVersion": run.rubric_version,
                }

            if run.status == EVALUATION_RUN_STATUS_FAILED:
                duration_ms = int((perf_counter() - started) * 1000)
                logger.warning(
                    "evaluation_generation_failed candidateSessionId=%s runId=%s jobId=%s durationMs=%s reason=%s",
                    context.candidate_session.id,
                    run.id,
                    job_id,
                    duration_ms,
                    "existing_failed_run",
                )
                return {
                    "status": "failed",
                    "candidateSessionId": context.candidate_session.id,
                    "evaluationRunId": run.id,
                    "errorCode": run.error_code or "evaluation_failed",
                    "durationMs": duration_ms,
                }
        else:
            run = await evaluation_runs.start_run(
                db,
                candidate_session_id=context.candidate_session.id,
                scenario_version_id=context.candidate_session.scenario_version_id,
                model_name=DEFAULT_EVALUATION_MODEL_NAME,
                model_version=DEFAULT_EVALUATION_MODEL_VERSION,
                prompt_version=DEFAULT_EVALUATION_PROMPT_VERSION,
                rubric_version=scenario_rubric_version,
                day2_checkpoint_sha=day2_checkpoint_sha,
                day3_final_sha=day3_final_sha,
                cutoff_commit_sha=cutoff_commit_sha,
                transcript_reference=transcript_reference,
                job_id=job_id,
                basis_fingerprint=basis_fingerprint,
                metadata_json=run_metadata,
                commit=False,
            )

        evaluator = evaluator_service.get_fit_profile_evaluator()
        bundle = evaluator_service.EvaluationInputBundle(
            candidate_session_id=context.candidate_session.id,
            scenario_version_id=context.candidate_session.scenario_version_id,
            model_name=DEFAULT_EVALUATION_MODEL_NAME,
            model_version=DEFAULT_EVALUATION_MODEL_VERSION,
            prompt_version=DEFAULT_EVALUATION_PROMPT_VERSION,
            rubric_version=scenario_rubric_version,
            disabled_day_indexes=disabled_days,
            day_inputs=day_inputs,
        )

        try:
            result = await evaluator.evaluate(bundle)
            day_scores = [
                {
                    "day_index": day_result.day_index,
                    "score": day_result.score,
                    "rubric_results_json": day_result.rubric_breakdown,
                    "evidence_pointers_json": day_result.evidence,
                }
                for day_result in result.day_results
            ]
            completed_run = await evaluation_runs.complete_run(
                db,
                run_id=run.id,
                day_scores=day_scores,
                overall_fit_score=result.overall_fit_score,
                recommendation=result.recommendation,
                confidence=result.confidence,
                raw_report_json=result.report_json,
                metadata_json=run_metadata,
                allow_empty_day_scores=True,
                commit=False,
            )
            marker_generated_at = completed_run.generated_at or datetime.now(UTC)
            await fit_profile_repository.upsert_marker(
                db,
                candidate_session_id=context.candidate_session.id,
                generated_at=marker_generated_at,
                commit=False,
            )
            await db.commit()
        except Exception as exc:
            await evaluation_runs.fail_run(
                db,
                run_id=run.id,
                error_code="evaluation_failed",
                error_message="evaluation_run_failed",
                metadata_json=run_metadata,
                commit=False,
            )
            await db.commit()
            duration_ms = int((perf_counter() - started) * 1000)
            logger.warning(
                "evaluation_generation_failed candidateSessionId=%s runId=%s jobId=%s durationMs=%s reason=%s",
                context.candidate_session.id,
                run.id,
                job_id,
                duration_ms,
                type(exc).__name__,
            )
            return {
                "status": "failed",
                "candidateSessionId": context.candidate_session.id,
                "evaluationRunId": run.id,
                "errorCode": "evaluation_failed",
                "durationMs": duration_ms,
            }

    duration_ms = int((perf_counter() - started) * 1000)
    logger.info(
        "evaluation_generation_completed candidateSessionId=%s runId=%s jobId=%s durationMs=%s modelVersion=%s promptVersion=%s rubricVersion=%s basisFingerprint=%s",
        context.candidate_session.id,
        completed_run.id,
        job_id,
        duration_ms,
        completed_run.model_version,
        completed_run.prompt_version,
        completed_run.rubric_version,
        completed_run.basis_fingerprint,
    )
    return {
        "status": "completed",
        "candidateSessionId": context.candidate_session.id,
        "evaluationRunId": completed_run.id,
        "basisFingerprint": completed_run.basis_fingerprint,
        "durationMs": duration_ms,
        "modelVersion": completed_run.model_version,
        "promptVersion": completed_run.prompt_version,
        "rubricVersion": completed_run.rubric_version,
    }


__all__ = [
    "DEFAULT_EVALUATION_MODEL_NAME",
    "DEFAULT_EVALUATION_MODEL_VERSION",
    "DEFAULT_EVALUATION_PROMPT_VERSION",
    "DEFAULT_RUBRIC_VERSION",
    "process_evaluation_run_job",
]
