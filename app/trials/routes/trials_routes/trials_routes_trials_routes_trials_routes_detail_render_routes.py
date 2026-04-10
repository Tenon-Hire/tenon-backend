"""Application module for trials routes trials routes trials routes detail render routes workflows."""

from __future__ import annotations

from collections.abc import Mapping

from app.ai import compute_ai_policy_snapshot_digest
from app.trials import services as sim_service
from app.trials.schemas.trials_schemas_trials_core_schema import (
    ScenarioVersionSummary,
    TrialDetailResponse,
    TrialDetailScenario,
    TrialDetailTask,
    build_trial_ai_config,
    build_trial_company_context,
    normalize_role_level,
)


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


def render_trial_detail(
    sim,
    tasks,
    active_scenario_version,
    *,
    pending_scenario_version=None,
    current_ai_policy_snapshot_json: Mapping[str, object] | None = None,
    active_bundle_status: str | None = None,
    pending_bundle_status: str | None = None,
) -> TrialDetailResponse:
    """Render trial detail."""
    raw_status = getattr(sim, "status", None)
    status_value = sim_service.normalize_trial_status_or_raise(raw_status)
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
                id=active_scenario_version.id,
                versionIndex=active_scenario_version.version_index,
                status=active_scenario_version.status,
                lockedAt=active_scenario_version.locked_at,
                storylineMd=active_scenario_version.storyline_md,
                taskPromptsJson=active_scenario_version.task_prompts_json,
                rubricJson=active_scenario_version.rubric_json,
                notes=active_scenario_version.focus_notes,
                modelName=active_scenario_version.model_name,
                modelVersion=active_scenario_version.model_version,
                promptVersion=active_scenario_version.prompt_version,
                rubricVersion=active_scenario_version.rubric_version,
                aiPolicySnapshotDigest=active_snapshot_digest,
                aiPromptPackVersion=(
                    active_snapshot_json.get("promptPackVersion")
                    if isinstance(active_snapshot_json, Mapping)
                    and isinstance(active_snapshot_json.get("promptPackVersion"), str)
                    else None
                ),
                precommitBundleStatus=active_bundle_status,
                agentRuntimeSummary=_scenario_agent_runtime_summary(
                    active_snapshot_json
                ),
            )
            if active_scenario_version is not None
            else None
        ),
        status=status_value,
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
