"""Application module for trials services trials scenario generation runtime service workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.ai import require_agent_policy_snapshot, require_ai_policy_snapshot
from app.trials.constants.trials_constants_trials_blueprints_constants import (
    DEFAULT_5_DAY_BLUEPRINT,
)
from app.trials.services.trials_services_trials_scenario_generation_constants import (
    CODE_PRIORITIES,
    DEBUG_SIGNALS,
    FALLBACK_MODEL_NAME,
    FALLBACK_MODEL_VERSION,
    SCENARIO_PROMPT_VERSION,
    SCENARIO_RUBRIC_VERSION,
    SCENARIO_SOURCE_TEMPLATE_FALLBACK,
    STORYLINE_CONSTRAINTS,
    STORYLINE_CONTEXTS,
)
from app.trials.services.trials_services_trials_scenario_generation_model import (
    GeneratedScenarioPayload,
    ScenarioGenerationMetadata,
)
from app.trials.services.trials_services_trials_scenario_generation_payloads_service import (
    build_rubric_json,
    build_task_prompts_json,
)
from app.trials.services.trials_services_trials_scenario_generation_story_service import (
    build_storyline_markdown,
    build_task_description,
)

PickFn = Callable[[tuple[str, ...], int, int], str]
TemplateNameFn = Callable[[str], str]
ChooseSourceFn = Callable[[], str]
GenerateLlmFn = Callable[..., GeneratedScenarioPayload]
FallbackBuilderFn = Callable[..., GeneratedScenarioPayload]


def _task_description_for_day(
    day_index: int,
    role: str,
    tech_stack: str,
    template_key: str,
    *,
    pick: PickFn,
    template_display_name: TemplateNameFn,
) -> str:
    return build_task_description(
        day_index=day_index,
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
        code_priorities=CODE_PRIORITIES,
        debug_signals=DEBUG_SIGNALS,
        pick=pick,
        template_display_name=template_display_name,
    )


def build_deterministic_template_scenario(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
    ai_policy_snapshot_json: dict[str, Any] | None,
    pick: PickFn,
    template_display_name: TemplateNameFn,
) -> GeneratedScenarioPayload:
    """Build deterministic template scenario."""
    require_ai_policy_snapshot(ai_policy_snapshot_json)
    storyline_md = build_storyline_markdown(
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
        storyline_contexts=STORYLINE_CONTEXTS,
        storyline_constraints=STORYLINE_CONSTRAINTS,
        pick=pick,
        template_display_name=template_display_name,
    )
    task_prompts_json = build_task_prompts_json(
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
        day_blueprint=DEFAULT_5_DAY_BLUEPRINT,
        task_description_builder=lambda day, r, t, k: _task_description_for_day(
            day, r, t, k, pick=pick, template_display_name=template_display_name
        ),
    )
    prestart_snapshot = require_agent_policy_snapshot(
        ai_policy_snapshot_json,
        "prestart",
    )
    return GeneratedScenarioPayload(
        storyline_md=storyline_md,
        task_prompts_json=task_prompts_json,
        rubric_json=build_rubric_json(role=role, tech_stack=tech_stack),
        codespace_spec_json={
            "task_kind": "feature",
            "summary": f"Baseline deterministic trial for {role}",
            "candidate_goal": (
                f"Complete the {role} implementation task inside the {template_key} template."
            ),
            "acceptance_criteria": [
                "Ship the requested task end-to-end.",
                "Keep the implementation testable and well-scoped.",
                "Document tradeoffs across design, coding, demo, and reflection stages.",
            ],
            "target_files": [],
            "repo_adjustments": [],
            "test_focus": ["core happy path", "edge-case behavior"],
            "test_command": None,
        },
        ai_policy_snapshot_json=ai_policy_snapshot_json,
        metadata=ScenarioGenerationMetadata(
            source=SCENARIO_SOURCE_TEMPLATE_FALLBACK,
            model_name=FALLBACK_MODEL_NAME,
            model_version=FALLBACK_MODEL_VERSION,
            prompt_version=str(
                prestart_snapshot.get("promptVersion") or SCENARIO_PROMPT_VERSION
            ),
            rubric_version=str(
                prestart_snapshot.get("rubricVersion") or SCENARIO_RUBRIC_VERSION
            ),
            template_key=template_key,
        ),
    )


def generate_scenario_payload(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
    scenario_template: str | None = None,
    focus: str | None = None,
    company_context: dict[str, Any] | None = None,
    company_prompt_overrides_json: dict[str, Any] | None = None,
    trial_prompt_overrides_json: dict[str, Any] | None = None,
    ai_policy_snapshot_json: dict[str, Any] | None = None,
    choose_source: ChooseSourceFn,
    generate_with_llm: GenerateLlmFn,
    build_fallback: FallbackBuilderFn,
    logger: Any,
) -> GeneratedScenarioPayload:
    """Generate scenario payload."""
    require_ai_policy_snapshot(ai_policy_snapshot_json)
    source = choose_source()
    if source == SCENARIO_SOURCE_TEMPLATE_FALLBACK:
        return build_fallback(
            role=role,
            tech_stack=tech_stack,
            template_key=template_key,
            ai_policy_snapshot_json=ai_policy_snapshot_json,
        )
    try:
        return generate_with_llm(
            role=role,
            tech_stack=tech_stack,
            template_key=template_key,
            scenario_template=scenario_template,
            focus=focus,
            company_context=company_context,
            company_prompt_overrides_json=company_prompt_overrides_json,
            trial_prompt_overrides_json=trial_prompt_overrides_json,
            ai_policy_snapshot_json=ai_policy_snapshot_json,
        )
    except Exception as exc:
        logger.warning(
            "scenario_generation_llm_failed",
            extra={"templateKey": template_key, "errorType": type(exc).__name__},
        )
        raise


__all__ = ["build_deterministic_template_scenario", "generate_scenario_payload"]
