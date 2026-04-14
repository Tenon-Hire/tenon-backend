"""Application module for trials routes trials routes trials routes detail render routes workflows."""

from __future__ import annotations

from collections.abc import Mapping

from app.ai import compute_ai_policy_snapshot_digest
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
from app.trials import services as sim_service
from app.trials.schemas.trials_schemas_trials_core_schema import (
    ScenarioVersionSummary,
    TrialDetailResponse,
    TrialDetailScenario,
    TrialDetailTask,
    TrialGenerationFailure,
    build_trial_ai_config,
    build_trial_company_context,
    normalize_role_level,
)

PUBLIC_JOB_STATUS_FAILED = "failed"


def _scenario_agent_runtime_summary(
    snapshot_json: Mapping[str, object] | None,
) -> list[dict[str, str]] | None:
    if not isinstance(snapshot_json, Mapping):
        return None
    raw_agents = snapshot_json.get("agents")
    if not isinstance(raw_agents, Mapping):
        return None
    summaries: list[dict[str, str]] = []
    for key in sorted(raw_agents):
        raw_agent = raw_agents.get(key)
        if not isinstance(raw_agent, Mapping):
            continue
        runtime = raw_agent.get("runtime")
        runtime_mode = (
            str(runtime.get("runtimeMode"))
            if isinstance(runtime, Mapping)
            and isinstance(runtime.get("runtimeMode"), str)
            else None
        )
        provider = (
            str(runtime.get("provider"))
            if isinstance(runtime, Mapping) and isinstance(runtime.get("provider"), str)
            else None
        )
        model = (
            str(runtime.get("model"))
            if isinstance(runtime, Mapping) and isinstance(runtime.get("model"), str)
            else None
        )
        prompt_version = (
            str(raw_agent.get("promptVersion"))
            if isinstance(raw_agent.get("promptVersion"), str)
            else None
        )
        rubric_version = (
            str(raw_agent.get("rubricVersion"))
            if isinstance(raw_agent.get("rubricVersion"), str)
            else None
        )
        summaries.append(
            {
                "key": str(key),
                "provider": provider or "",
                "model": model or "",
                "runtimeMode": runtime_mode or "",
                "promptVersion": prompt_version or "",
                "rubricVersion": rubric_version or "",
            }
        )
    return summaries or None


def _scenario_snapshot_summary(
    scenario_version,
    *,
    bundle_status: str | None,
) -> dict[str, object] | None:
    if scenario_version is None:
        return None
    snapshot_json = getattr(scenario_version, "ai_policy_snapshot_json", None)
    if not isinstance(snapshot_json, Mapping):
        return None
    return {
        "scenarioVersionId": scenario_version.id,
        "snapshotDigest": compute_ai_policy_snapshot_digest(snapshot_json),
        "promptPackVersion": snapshot_json.get("promptPackVersion")
        if isinstance(snapshot_json.get("promptPackVersion"), str)
        else None,
        "bundleStatus": bundle_status,
        "agents": _scenario_agent_runtime_summary(snapshot_json),
    }


def _latest_relevant_scenario_version(
    *,
    active_scenario_version,
    pending_scenario_version,
):
    if _scenario_version_is_reviewable(pending_scenario_version):
        return pending_scenario_version
    if _scenario_version_is_reviewable(active_scenario_version):
        return active_scenario_version
    if pending_scenario_version is not None:
        return pending_scenario_version
    return active_scenario_version


def _scenario_version_is_reviewable(scenario_version) -> bool:
    return bool(
        scenario_version is not None
        and getattr(scenario_version, "status", None) in {"ready", "locked"}
    )


def _scenario_review_bundle_status(
    *,
    active_scenario_version,
    pending_scenario_version,
    active_bundle_status: str | None,
    pending_bundle_status: str | None,
) -> str | None:
    if pending_scenario_version is not None:
        return pending_bundle_status
    if active_scenario_version is not None:
        return active_bundle_status
    return None


def _generation_failure_summary(
    scenario_generation_job,
) -> TrialGenerationFailure | None:
    if scenario_generation_job is None:
        return None
    job_status = getattr(scenario_generation_job, "status", None)
    if job_status not in {JOB_STATUS_DEAD_LETTER, PUBLIC_JOB_STATUS_FAILED}:
        return None
    return TrialGenerationFailure(
        jobId=scenario_generation_job.id,
        status="failed",
        error=getattr(scenario_generation_job, "last_error", None),
        retryable=True,
        canRetry=True,
    )


def _generation_status(
    *,
    active_scenario_version,
    pending_scenario_version,
    scenario_generation_job,
    generation_failure: TrialGenerationFailure | None,
) -> str:
    if generation_failure is not None:
        return "failed"
    pending_status = getattr(pending_scenario_version, "status", None)
    active_status = getattr(active_scenario_version, "status", None)
    job_status = getattr(scenario_generation_job, "status", None)
    if pending_status == "generating" or active_status == "generating":
        return "generating"
    if job_status in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        return "generating"
    if _scenario_version_is_reviewable(pending_scenario_version):
        return "ready_for_review"
    if _scenario_version_is_reviewable(active_scenario_version):
        return "ready_for_review"
    if (
        pending_scenario_version is None
        and active_scenario_version is None
        and scenario_generation_job is None
    ):
        return "not_started"
    return "not_started"


def render_trial_detail(
    sim,
    tasks,
    active_scenario_version,
    *,
    pending_scenario_version=None,
    current_ai_policy_snapshot_json: Mapping[str, object] | None = None,
    active_bundle_status: str | None = None,
    pending_bundle_status: str | None = None,
    scenario_generation_job=None,
) -> TrialDetailResponse:
    """Render trial detail."""
    raw_status = getattr(sim, "status", None)
    status_value = sim_service.normalize_trial_status_or_raise(raw_status)
    review_scenario_version = _latest_relevant_scenario_version(
        active_scenario_version=active_scenario_version,
        pending_scenario_version=pending_scenario_version,
    )
    review_snapshot_json = getattr(
        review_scenario_version, "ai_policy_snapshot_json", None
    )
    active_snapshot_json = getattr(
        active_scenario_version, "ai_policy_snapshot_json", None
    )
    active_snapshot_digest = compute_ai_policy_snapshot_digest(active_snapshot_json)
    current_snapshot_digest = compute_ai_policy_snapshot_digest(
        current_ai_policy_snapshot_json
    )
    current_prompt_pack_version = (
        current_ai_policy_snapshot_json.get("promptPackVersion")
        if isinstance(current_ai_policy_snapshot_json, Mapping)
        and isinstance(current_ai_policy_snapshot_json.get("promptPackVersion"), str)
        else None
    )
    generation_failure = _generation_failure_summary(scenario_generation_job)
    scenario_locked = bool(
        review_scenario_version is not None
        and getattr(review_scenario_version, "locked_at", None) is not None
    )
    generation_status = _generation_status(
        active_scenario_version=active_scenario_version,
        pending_scenario_version=pending_scenario_version,
        scenario_generation_job=scenario_generation_job,
        generation_failure=generation_failure,
    )
    can_approve_scenario = bool(
        review_scenario_version is not None
        and review_scenario_version.status == "ready"
        and not scenario_locked
        and (
            pending_scenario_version is None
            or getattr(review_scenario_version, "id", None)
            == getattr(pending_scenario_version, "id", None)
        )
    )
    can_activate_trial = bool(scenario_locked and status_value == "ready_for_review")
    return TrialDetailResponse(
        id=sim.id,
        title=sim.title,
        templateKey=sim.template_key,
        role=sim.role,
        seniority=normalize_role_level(getattr(sim, "seniority", None))
        or getattr(sim, "seniority", None),
        techStack=sim.tech_stack,
        focus=sim.focus,
        companyContext=build_trial_company_context(
            getattr(sim, "company_context", None)
        ),
        ai=build_trial_ai_config(
            notice_version=getattr(sim, "ai_notice_version", None),
            notice_text=getattr(sim, "ai_notice_text", None),
            eval_enabled_by_day=getattr(sim, "ai_eval_enabled_by_day", None),
            prompt_overrides_json=getattr(sim, "ai_prompt_overrides_json", None),
            prompt_pack_version=current_prompt_pack_version,
            changes_pending_regeneration=bool(
                active_snapshot_digest
                and current_snapshot_digest
                and active_snapshot_digest != current_snapshot_digest
            ),
            active_scenario_snapshot=_scenario_snapshot_summary(
                active_scenario_version,
                bundle_status=active_bundle_status,
            ),
            pending_scenario_snapshot=_scenario_snapshot_summary(
                pending_scenario_version,
                bundle_status=pending_bundle_status,
            ),
        ),
        activeScenarioVersionId=getattr(sim, "active_scenario_version_id", None),
        pendingScenarioVersionId=getattr(sim, "pending_scenario_version_id", None),
        scenario=(
            TrialDetailScenario(
                id=review_scenario_version.id,
                versionIndex=review_scenario_version.version_index,
                status=review_scenario_version.status,
                lockedAt=review_scenario_version.locked_at,
                storylineMd=review_scenario_version.storyline_md,
                taskPromptsJson=review_scenario_version.task_prompts_json,
                rubricJson=review_scenario_version.rubric_json,
                notes=review_scenario_version.focus_notes,
                modelName=review_scenario_version.model_name,
                modelVersion=review_scenario_version.model_version,
                promptVersion=review_scenario_version.prompt_version,
                rubricVersion=review_scenario_version.rubric_version,
                aiPolicySnapshotDigest=compute_ai_policy_snapshot_digest(
                    review_snapshot_json
                ),
                aiPromptPackVersion=(
                    review_snapshot_json.get("promptPackVersion")
                    if isinstance(review_snapshot_json, Mapping)
                    and isinstance(review_snapshot_json.get("promptPackVersion"), str)
                    else None
                ),
                precommitBundleStatus=_scenario_review_bundle_status(
                    active_scenario_version=active_scenario_version,
                    pending_scenario_version=pending_scenario_version,
                    active_bundle_status=active_bundle_status,
                    pending_bundle_status=pending_bundle_status,
                ),
                agentRuntimeSummary=_scenario_agent_runtime_summary(
                    getattr(review_scenario_version, "ai_policy_snapshot_json", None)
                ),
            )
            if review_scenario_version is not None
            else None
        ),
        status=status_value,
        generationStatus=generation_status,
        generationFailure=generation_failure,
        scenarioLocked=scenario_locked,
        canApproveScenario=can_approve_scenario,
        canActivateTrial=can_activate_trial,
        canRetryGeneration=generation_failure is not None,
        generatingAt=getattr(sim, "generating_at", None),
        readyForReviewAt=getattr(sim, "ready_for_review_at", None),
        activatedAt=getattr(sim, "activated_at", None),
        terminatedAt=getattr(sim, "terminated_at", None),
        scenarioVersionSummary=ScenarioVersionSummary(
            templateKey=getattr(sim, "template_key", None),
            scenarioTemplate=getattr(sim, "scenario_template", None),
        ),
        tasks=[
            TrialDetailTask(
                dayIndex=task.day_index,
                title=task.title,
                type=task.type,
                description=task.description,
                rubric=None,
                maxScore=task.max_score,
                templateRepoFullName=(
                    task.template_repo
                    if task.day_index in {2, 3} and task.template_repo
                    else None
                ),
            )
            for task in tasks
        ],
    )
