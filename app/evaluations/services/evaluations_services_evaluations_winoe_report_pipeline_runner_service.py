"""Application module for evaluations services evaluations winoe report pipeline runner service workflows."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.ai import (
    compute_ai_policy_snapshot_digest,
    require_agent_policy_snapshot,
    require_agent_runtime,
    require_candidate_settings_from_snapshot,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_constants_service import (
    DEFAULT_EVALUATION_MODEL_NAME,
    DEFAULT_EVALUATION_MODEL_VERSION,
    DEFAULT_EVALUATION_PROMPT_VERSION,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_day_inputs_service import (
    _build_day_inputs,
    _resolve_rubric_version,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_execute_service import (
    _evaluate_and_finalize_run,
    _mark_failed_run,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_metadata_service import (
    _build_run_metadata,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_parse_service import (
    _normalize_day_toggles,
    _normalize_transcript_segments,
    _parse_positive_int,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_run_state_service import (
    _completed_response,
    _get_or_start_run,
)
from app.integrations.winoe_report_review import WinoeReportReviewProviderError

_RETRYABLE_PROVIDER_ERROR_MARKERS = (
    "ratelimiterror",
    "too many requests",
    "rate limit",
    "429",
    "apitimeouterror",
    "apiconnectionerror",
    "internalservererror",
    "serviceunavailableerror",
    "overloadederror",
)


def _is_retryable_winoe_report_provider_error(error: Exception) -> bool:
    if not isinstance(error, WinoeReportReviewProviderError):
        return False
    normalized = str(error).strip().lower()
    if not normalized:
        return False
    return any(marker in normalized for marker in _RETRYABLE_PROVIDER_ERROR_MARKERS)


async def process_evaluation_run_job_impl(
    payload_json: dict[str, Any], **deps
) -> dict[str, Any]:
    """Process evaluation run job impl."""
    started = perf_counter()
    session_id = _parse_positive_int(payload_json.get("candidateSessionId"))
    company_id = _parse_positive_int(payload_json.get("companyId"))
    user_id = _parse_positive_int(payload_json.get("requestedByUserId"))
    job_id = (
        payload_json.get("jobId")
        if isinstance(payload_json.get("jobId"), str)
        else None
    )
    if session_id is None or company_id is None:
        return {
            "status": "skipped_invalid_payload",
            "candidateSessionId": session_id,
            "companyId": company_id,
        }

    deps["logger"].info(
        "evaluation_generation_started candidateSessionId=%s companyId=%s jobId=%s",
        session_id,
        company_id,
        job_id,
    )
    async with deps["async_session_maker"]() as db:
        context = await deps["get_candidate_session_evaluation_context"](
            db, candidate_session_id=session_id
        )
        if context is None:
            return {
                "status": "candidate_session_not_found",
                "candidateSessionId": session_id,
            }
        if not deps["has_company_access"](
            trial_company_id=context.trial.company_id,
            expected_company_id=company_id,
        ):
            return {
                "status": "company_access_forbidden",
                "candidateSessionId": session_id,
            }

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
        enabled_days, disabled_days = _normalize_day_toggles(
            snapshot_eval_enabled_by_day
        )
        tasks = await deps["_tasks_by_day"](db, trial_id=context.trial.id)
        submissions = await deps["_submissions_by_day"](
            db,
            candidate_session_id=context.candidate_session.id,
            trial_id=context.trial.id,
        )
        audits = await deps["_day_audits_by_day"](
            db, candidate_session_id=context.candidate_session.id
        )
        transcript, transcript_ref = await deps["_resolve_day4_transcript"](
            db,
            candidate_session_id=context.candidate_session.id,
            day4_task=tasks.get(4),
            day4_submission=submissions.get(4),
        )

        day_inputs = _build_day_inputs(
            tasks_by_day=tasks,
            submissions_by_day=submissions,
            day_audits=audits,
            transcript_reference=transcript_ref,
            normalized_segments=_normalize_transcript_segments(
                transcript.segments_json if transcript else None
            ),
        )

        rubric_version = _resolve_rubric_version(context)
        run_metadata, _basis_refs, day2_sha, day3_sha, cutoff_sha = _build_run_metadata(
            context=context,
            scenario_rubric_version=rubric_version,
            day_audits=audits,
            submissions_by_day=submissions,
            transcript_reference=transcript_ref,
            transcript=transcript,
            disabled_days=disabled_days,
            enabled_days=enabled_days,
            requested_by_user_id=user_id,
            job_id=job_id,
            ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
                ai_policy_snapshot_json
            ),
        )
        run, terminal_response = await _get_or_start_run(
            db=db,
            context=context,
            evaluation_repo=deps["evaluation_repo"],
            evaluation_runs=deps["evaluation_runs"],
            job_id=job_id,
            started=started,
            run_metadata=run_metadata,
            basis_fingerprint=run_metadata["basisFingerprint"],
            scenario_rubric_version=rubric_version,
            day2_checkpoint_sha=day2_sha,
            day3_final_sha=day3_sha,
            cutoff_commit_sha=cutoff_sha,
            transcript_reference=transcript_ref,
        )
        if terminal_response is not None:
            return terminal_response

        aggregator_snapshot = require_agent_policy_snapshot(
            ai_policy_snapshot_json,
            "winoeReport",
            scenario_version_id=context.candidate_session.scenario_version_id,
        )
        aggregator_runtime = require_agent_runtime(
            ai_policy_snapshot_json,
            "winoeReport",
            scenario_version_id=context.candidate_session.scenario_version_id,
        )
        bundle = deps["evaluator_service"].EvaluationInputBundle(
            candidate_session_id=context.candidate_session.id,
            scenario_version_id=context.candidate_session.scenario_version_id,
            model_name=str(aggregator_runtime["model"])
            or DEFAULT_EVALUATION_MODEL_NAME,
            model_version=(
                str(aggregator_runtime["model"]) or DEFAULT_EVALUATION_MODEL_VERSION
            ),
            prompt_version=(
                str(aggregator_snapshot["promptVersion"])
                or DEFAULT_EVALUATION_PROMPT_VERSION
            ),
            rubric_version=rubric_version,
            disabled_day_indexes=disabled_days,
            day_inputs=day_inputs,
            trial_context_json={
                "trialId": context.trial.id,
                "title": getattr(context.trial, "title", None),
                "role": getattr(context.trial, "role", None),
                "techStack": getattr(context.trial, "tech_stack", None),
                "seniority": getattr(context.trial, "seniority", None),
                "templateKey": getattr(context.trial, "template_key", None),
                "focus": getattr(context.trial, "focus", None),
                "companyContext": getattr(context.trial, "company_context", None),
                "storylineMd": getattr(context.scenario_version, "storyline_md", None),
                "rubricJson": getattr(context.scenario_version, "rubric_json", None),
                "codespaceSpecJson": getattr(
                    context.scenario_version, "codespace_spec_json", None
                ),
            },
            ai_policy_snapshot_json=ai_policy_snapshot_json,
            ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
                ai_policy_snapshot_json
            ),
        )
        try:
            completed_run = await _evaluate_and_finalize_run(
                db=db,
                run=run,
                evaluator=deps["evaluator_service"].get_winoe_report_evaluator(),
                bundle=bundle,
                evaluation_runs=deps["evaluation_runs"],
                winoe_report_repository=deps["winoe_report_repository"],
                context=context,
                run_metadata=run_metadata,
            )
        except Exception as exc:
            if _is_retryable_winoe_report_provider_error(exc):
                deps["logger"].warning(
                    "evaluation_generation_retryable_failure candidateSessionId=%s jobId=%s durationMs=%s reason=%s",
                    context.candidate_session.id,
                    job_id,
                    int((perf_counter() - started) * 1000),
                    type(exc).__name__,
                )
                raise
            await _mark_failed_run(
                db=db,
                run=run,
                evaluation_runs=deps["evaluation_runs"],
                run_metadata=run_metadata,
            )
            deps["logger"].warning(
                "evaluation_generation_failed candidateSessionId=%s runId=%s jobId=%s durationMs=%s reason=%s",
                context.candidate_session.id,
                run.id,
                job_id,
                int((perf_counter() - started) * 1000),
                type(exc).__name__,
            )
            return {
                "status": "failed",
                "candidateSessionId": context.candidate_session.id,
                "evaluationRunId": run.id,
                "errorCode": "evaluation_failed",
                "durationMs": int((perf_counter() - started) * 1000),
            }

    duration_ms = int((perf_counter() - started) * 1000)
    deps["logger"].info(
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
    return _completed_response(
        run=completed_run,
        candidate_session_id=context.candidate_session.id,
        duration_ms=duration_ms,
    )


__all__ = ["process_evaluation_run_job_impl"]
