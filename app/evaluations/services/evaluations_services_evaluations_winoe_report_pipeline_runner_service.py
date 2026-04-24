"""Application module for evaluations services evaluations winoe report pipeline runner service workflows."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.ai import (
    AIPolicySnapshotError,
    compute_ai_policy_snapshot_basis_fingerprint,
    compute_ai_policy_snapshot_digest,
    get_agent_policy_snapshot,
    require_agent_policy_snapshot,
    require_agent_runtime,
    require_candidate_settings_from_snapshot,
    validate_ai_policy_snapshot_contract,
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
    _resolve_cutoff_commit_shas,
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
from app.evaluations.services.evaluations_services_evaluations_winoe_rubric_snapshots_service import (
    get_rubric_snapshots_for_scenario_version,
)
from app.integrations.winoe_report_review import WinoeReportReviewProviderError
from app.media.repositories.transcripts import repository as transcripts_repo
from app.shared.utils.shared_utils_project_brief_service import (
    canonical_project_brief_markdown,
)

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


async def _record_invalid_snapshot_run(
    *,
    db,
    context,
    evaluation_runs,
    ai_policy_snapshot_json: dict[str, Any] | None,
    job_id: str | None,
    rubric_version: str,
    day2_checkpoint_sha: str,
    day3_final_sha: str,
    cutoff_commit_sha: str,
    transcript_reference: str,
    error: AIPolicySnapshotError,
) -> Any:
    snapshot_fingerprint = compute_ai_policy_snapshot_basis_fingerprint(
        ai_policy_snapshot_json
    )
    snapshot_digest = compute_ai_policy_snapshot_digest(ai_policy_snapshot_json)
    snapshot_metadata: dict[str, Any] = {
        "candidateSessionId": context.candidate_session.id,
        "scenarioVersionId": context.candidate_session.scenario_version_id,
        "jobId": job_id,
        "aiPolicySnapshotDigest": snapshot_digest,
        "aiPolicySnapshotBasisFingerprint": snapshot_fingerprint,
        "snapshotValidationErrorCode": getattr(
            error, "error_code", "scenario_version_ai_policy_snapshot_invalid"
        ),
        "snapshotValidationMessage": str(error),
        "evaluationModelName": DEFAULT_EVALUATION_MODEL_NAME,
        "evaluationModelVersion": DEFAULT_EVALUATION_MODEL_VERSION,
        "evaluationPromptVersion": DEFAULT_EVALUATION_PROMPT_VERSION,
        "evaluationRubricVersion": rubric_version,
        "aiPolicyProvider": None,
        "aiPolicyModel": None,
        "aiPolicyPromptVersion": None,
        "aiPolicyRubricVersion": None,
    }
    details = getattr(error, "details", None)
    if isinstance(details, dict) and details:
        snapshot_metadata["snapshotValidationDetails"] = details
    winoe_report_snapshot = get_agent_policy_snapshot(
        ai_policy_snapshot_json, "winoeReport"
    )
    if isinstance(winoe_report_snapshot, dict):
        snapshot_metadata["aiPolicyProvider"] = winoe_report_snapshot.get("provider")
        snapshot_metadata["aiPolicyModel"] = winoe_report_snapshot.get("model")
        snapshot_metadata["aiPolicyPromptVersion"] = winoe_report_snapshot.get(
            "promptVersion"
        )
        snapshot_metadata["aiPolicyRubricVersion"] = winoe_report_snapshot.get(
            "rubricVersion"
        )
    run = await evaluation_runs.start_run(
        db,
        candidate_session_id=context.candidate_session.id,
        scenario_version_id=context.candidate_session.scenario_version_id,
        model_name=DEFAULT_EVALUATION_MODEL_NAME,
        model_version=DEFAULT_EVALUATION_MODEL_VERSION,
        prompt_version=DEFAULT_EVALUATION_PROMPT_VERSION,
        rubric_version=rubric_version,
        day2_checkpoint_sha=day2_checkpoint_sha,
        day3_final_sha=day3_final_sha,
        cutoff_commit_sha=cutoff_commit_sha,
        transcript_reference=transcript_reference,
        job_id=job_id,
        basis_fingerprint=snapshot_fingerprint,
        metadata_json=snapshot_metadata,
        commit=False,
    )
    failed_run = await evaluation_runs.fail_run(
        db,
        run_id=run.id,
        error_code=getattr(
            error, "error_code", "scenario_version_ai_policy_snapshot_invalid"
        ),
        metadata_json=snapshot_metadata,
        error_message=str(error),
        commit=False,
    )
    await db.commit()
    return failed_run


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
        tasks = await deps["_tasks_by_day"](db, trial_id=context.trial.id)
        submissions = await deps["_submissions_by_day"](
            db,
            candidate_session_id=context.candidate_session.id,
            trial_id=context.trial.id,
        )
        audits = await deps["_day_audits_by_day"](
            db, candidate_session_id=context.candidate_session.id
        )
        transcript_resolution = await deps["_resolve_day4_transcript"](
            db,
            candidate_session_id=context.candidate_session.id,
            day4_task=tasks.get(4),
            day4_submission=submissions.get(4),
        )
        transcript_state = getattr(
            transcript_resolution,
            "transcript_state",
            transcripts_repo.TRANSCRIPT_EVALUATION_STATE_MISSING,
        )
        try:
            transcript, transcript_ref, transcript_state = transcript_resolution
        except ValueError:
            transcript, transcript_ref = transcript_resolution
        day4_disabled = transcript_state != "ready"
        rubric_version = _resolve_rubric_version(context)
        day2_checkpoint_sha, day3_sha, cutoff_sha = _resolve_cutoff_commit_shas(
            day_audits=audits,
            submissions_by_day=submissions,
        )
        enabled_days: list[int] = []
        disabled_days: list[int] = []
        effective_ai_policy_snapshot_json: dict[str, Any] = (
            ai_policy_snapshot_json if isinstance(ai_policy_snapshot_json, dict) else {}
        )
        rubric_snapshots: list[dict[str, Any]] = []
        try:
            validate_ai_policy_snapshot_contract(
                ai_policy_snapshot_json,
                scenario_version_id=context.candidate_session.scenario_version_id,
            )
            (
                _snapshot_notice_version,
                _snapshot_notice_text,
                snapshot_eval_enabled_by_day,
            ) = require_candidate_settings_from_snapshot(
                ai_policy_snapshot_json,
                scenario_version_id=context.candidate_session.scenario_version_id,
            )
            rubric_snapshot_context = await get_rubric_snapshots_for_scenario_version(
                db,
                scenario_version=context.scenario_version,
                trial=context.trial,
            )
            effective_ai_policy_snapshot_json = rubric_snapshot_context[
                "effectiveAiPolicySnapshotJson"
            ]
            rubric_snapshots = list(rubric_snapshot_context["rubricSnapshots"])
        except AIPolicySnapshotError as exc:
            failed_run = await _record_invalid_snapshot_run(
                db=db,
                context=context,
                evaluation_runs=deps["evaluation_runs"],
                ai_policy_snapshot_json=ai_policy_snapshot_json,
                job_id=job_id,
                rubric_version=rubric_version,
                day2_checkpoint_sha=day2_checkpoint_sha,
                day3_final_sha=day3_sha,
                cutoff_commit_sha=cutoff_sha,
                transcript_reference=transcript_ref,
                error=exc,
            )
            return {
                "status": "failed",
                "candidateSessionId": context.candidate_session.id,
                "evaluationRunId": failed_run.id,
                "errorCode": getattr(
                    exc, "error_code", "scenario_version_ai_policy_snapshot_invalid"
                ),
                "durationMs": int((perf_counter() - started) * 1000),
            }
        enabled_days, disabled_days = _normalize_day_toggles(
            snapshot_eval_enabled_by_day
        )
        effective_disabled_days = list(disabled_days)
        if day4_disabled:
            effective_disabled_days.append(4)
        effective_disabled_days = sorted(set(effective_disabled_days))

        day_inputs = _build_day_inputs(
            tasks_by_day=tasks,
            submissions_by_day=submissions,
            day_audits=audits,
            transcript_reference=transcript_ref,
            normalized_segments=(
                _normalize_transcript_segments(
                    transcript.segments_json
                    if transcript and not day4_disabled
                    else None
                )
                if not day4_disabled
                else []
            ),
        )

        run_metadata, _basis_refs, day2_sha, day3_sha, cutoff_sha = _build_run_metadata(
            context=context,
            scenario_rubric_version=rubric_version,
            day_audits=audits,
            submissions_by_day=submissions,
            transcript_reference=transcript_ref,
            transcript=transcript,
            disabled_days=effective_disabled_days,
            enabled_days=enabled_days,
            requested_by_user_id=user_id,
            job_id=job_id,
            ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
                effective_ai_policy_snapshot_json
            ),
            basis_ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
                rubric_snapshot_context["aiPolicySnapshotJson"]
            ),
            rubric_snapshots=rubric_snapshots,
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
            effective_ai_policy_snapshot_json,
            "winoeReport",
            scenario_version_id=context.candidate_session.scenario_version_id,
        )
        aggregator_runtime = require_agent_runtime(
            effective_ai_policy_snapshot_json,
            "winoeReport",
            scenario_version_id=context.candidate_session.scenario_version_id,
        )
        run_metadata.update(
            {
                "aiPolicyProvider": str(aggregator_runtime["provider"]),
                "aiPolicyModel": str(aggregator_runtime["model"]),
                "aiPolicyModelVersion": str(aggregator_runtime["model"]),
                "aiPolicyPromptVersion": str(aggregator_snapshot["promptVersion"]),
                "aiPolicyRubricVersion": rubric_version,
                "rubricSnapshots": rubric_snapshots,
            }
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
            disabled_day_indexes=effective_disabled_days,
            day_inputs=day_inputs,
            trial_context_json={
                "trialId": context.trial.id,
                "title": getattr(context.trial, "title", None),
                "role": getattr(context.trial, "role", None),
                "techStack": getattr(context.trial, "tech_stack", None),
                "seniority": getattr(context.trial, "seniority", None),
                "focus": getattr(context.trial, "focus", None),
                "companyContext": getattr(context.trial, "company_context", None),
                "storylineMd": getattr(context.scenario_version, "storyline_md", None),
                "rubricJson": getattr(context.scenario_version, "rubric_json", None),
                "projectBriefMd": canonical_project_brief_markdown(
                    context.scenario_version,
                    trial_title=getattr(context.trial, "title", None),
                    storyline_md=getattr(
                        context.scenario_version, "storyline_md", None
                    ),
                ),
            },
            ai_policy_snapshot_json=effective_ai_policy_snapshot_json,
            ai_policy_snapshot_digest=compute_ai_policy_snapshot_digest(
                effective_ai_policy_snapshot_json
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
                error_code=getattr(exc, "error_code", "evaluation_failed"),
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
                "errorCode": getattr(exc, "error_code", "evaluation_failed"),
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
