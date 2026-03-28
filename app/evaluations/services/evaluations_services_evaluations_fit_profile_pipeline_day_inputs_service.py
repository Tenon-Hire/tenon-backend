"""Application module for evaluations services evaluations fit profile pipeline day inputs service workflows."""

from __future__ import annotations

from app.evaluations.services import (
    evaluations_services_evaluations_evaluator_service as evaluator_service,
)
from app.evaluations.services.evaluations_services_evaluations_fit_profile_pipeline_constants_service import (
    DEFAULT_RUBRIC_VERSION,
)
from app.evaluations.services.evaluations_services_evaluations_fit_profile_pipeline_parse_service import (
    _parse_diff_summary,
)
from app.shared.database.shared_database_models_model import (
    CandidateDayAudit,
    Submission,
    Task,
)


def _resolve_rubric_version(context) -> str:
    version = getattr(
        getattr(context, "scenario_version", None), "rubric_version", None
    )
    return (
        version
        if isinstance(version, str) and version.strip()
        else DEFAULT_RUBRIC_VERSION
    )


def _build_day_inputs(
    *,
    tasks_by_day: dict[int, Task],
    submissions_by_day: dict[int, Submission],
    day_audits: dict[int, CandidateDayAudit],
    transcript_reference: str,
    normalized_segments: list[dict[str, object]],
) -> list[evaluator_service.DayEvaluationInput]:
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
                repo_full_name=submission.code_repo_path
                if submission is not None
                else None,
                commit_sha=submission.commit_sha if submission is not None else None,
                workflow_run_id=submission.workflow_run_id
                if submission is not None
                else None,
                diff_summary=(
                    _parse_diff_summary(submission.diff_summary_json)
                    if submission is not None
                    else None
                ),
                tests_passed=submission.tests_passed
                if submission is not None
                else None,
                tests_failed=submission.tests_failed
                if submission is not None
                else None,
                transcript_reference=transcript_reference if day_index == 4 else None,
                transcript_segments=normalized_segments if day_index == 4 else [],
                cutoff_commit_sha=(
                    day_audit.cutoff_commit_sha if day_audit is not None else None
                ),
                eval_basis_ref=day_audit.eval_basis_ref
                if day_audit is not None
                else None,
            )
        )
    return day_inputs


__all__ = ["_build_day_inputs", "_resolve_rubric_version"]
