"""Application module for evaluations services evaluations winoe report api service workflows."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import (
    compute_ai_policy_snapshot_digest,
    require_candidate_settings_from_snapshot,
)
from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.services.evaluations_services_evaluations_winoe_report_access_service import (
    CandidateSessionEvaluationContext,
    get_candidate_session_evaluation_context,
    has_company_access,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_api_helpers_service import (
    build_latest_run_status,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_api_helpers_service import (
    has_active_evaluation_job as _has_active_evaluation_job_impl,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_composer_service import (
    build_ready_payload,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_jobs_service import (
    EVALUATION_RUN_JOB_TYPE,
    enqueue_evaluation_run,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_day_inputs_service import (
    _resolve_rubric_version,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_metadata_service import (
    _build_run_metadata,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_parse_service import (
    _normalize_day_toggles,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_queries_service import (
    _day_audits_by_day,
    _submissions_by_day,
    _tasks_by_day,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_transcript_service import (
    _resolve_day4_transcript,
)
from app.shared.database.shared_database_models_model import User


async def _has_active_evaluation_job(
    db: AsyncSession,
    *,
    candidate_session_id: int,
) -> bool:
    return await _has_active_evaluation_job_impl(
        db,
        candidate_session_id=candidate_session_id,
        job_type=EVALUATION_RUN_JOB_TYPE,
    )


async def require_talent_partner_candidate_session_context(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    user: User,
) -> CandidateSessionEvaluationContext:
    """Require Talent Partner candidate session context."""
    context = await get_candidate_session_evaluation_context(
        db,
        candidate_session_id=candidate_session_id,
    )
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found"
        )
    if not has_company_access(
        trial_company_id=context.trial.company_id,
        expected_company_id=getattr(user, "company_id", None),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate session access forbidden",
        )
    return context


async def _build_generation_basis_fingerprint(
    db: AsyncSession, *, context: CandidateSessionEvaluationContext
) -> str:
    ai_policy_snapshot_json = getattr(
        context.scenario_version, "ai_policy_snapshot_json", None
    )
    (
        _snapshot_notice_version,
        _snapshot_notice_text,
        snapshot_eval_enabled_by_day,
    ) = require_candidate_settings_from_snapshot(
        ai_policy_snapshot_json,
        scenario_version_id=context.candidate_session.scenario_version_id,
    )
    enabled_days, disabled_days = _normalize_day_toggles(snapshot_eval_enabled_by_day)
    tasks = await _tasks_by_day(db, trial_id=context.trial.id)
    submissions = await _submissions_by_day(
        db,
        candidate_session_id=context.candidate_session.id,
        trial_id=context.trial.id,
    )
    audits = await _day_audits_by_day(
        db, candidate_session_id=context.candidate_session.id
    )
    transcript_resolution = await _resolve_day4_transcript(
        db,
        candidate_session_id=context.candidate_session.id,
        day4_task=tasks.get(4),
        day4_submission=submissions.get(4),
    )
    transcript_state = getattr(
        transcript_resolution,
        "transcript_state",
        "missing",
    )
    try:
        transcript, transcript_ref, transcript_state = transcript_resolution
    except ValueError:
        transcript, transcript_ref = transcript_resolution
    day4_disabled = transcript_state != "ready"
    effective_disabled_days = list(disabled_days)
    if day4_disabled:
        effective_disabled_days.append(4)
    effective_disabled_days = sorted(set(effective_disabled_days))
    rubric_version = _resolve_rubric_version(context)
    run_metadata, _basis_refs, _day2_sha, _day3_sha, _cutoff_sha = _build_run_metadata(
        context=context,
        scenario_rubric_version=rubric_version,
        day_audits=audits,
        submissions_by_day=submissions,
        transcript_reference=transcript_ref,
        transcript=transcript,
        disabled_days=effective_disabled_days,
        enabled_days=enabled_days,
        requested_by_user_id=None,
        job_id=None,
        ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
            ai_policy_snapshot_json
        ),
    )
    return str(run_metadata["basisFingerprint"])


async def generate_winoe_report(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    user: User,
) -> dict[str, Any]:
    """Generate winoe report."""
    context = await require_talent_partner_candidate_session_context(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    basis_fingerprint = await _build_generation_basis_fingerprint(db, context=context)
    job = await enqueue_evaluation_run(
        db,
        candidate_session_id=context.candidate_session.id,
        company_id=context.trial.company_id,
        requested_by_user_id=user.id,
        basis_fingerprint=basis_fingerprint,
        commit=True,
    )
    return {"jobId": job.id, "status": "queued"}


async def fetch_winoe_report(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    user: User,
) -> dict[str, Any]:
    """Return winoe report."""
    context = await require_talent_partner_candidate_session_context(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    session_id = context.candidate_session.id
    latest_success = (
        await evaluation_repo.get_latest_successful_run_for_candidate_session(
            db,
            candidate_session_id=session_id,
        )
    )
    if latest_success is not None:
        return build_ready_payload(latest_success)

    latest_run = await evaluation_repo.get_latest_run_for_candidate_session(
        db,
        candidate_session_id=session_id,
    )
    if latest_run is not None:
        if latest_run.status == "completed":
            return build_ready_payload(latest_run)
        return build_latest_run_status(latest_run)

    if await _has_active_evaluation_job(db, candidate_session_id=session_id):
        return {"status": "running"}
    return {"status": "not_started"}


__all__ = [
    "fetch_winoe_report",
    "generate_winoe_report",
    "require_talent_partner_candidate_session_context",
]
