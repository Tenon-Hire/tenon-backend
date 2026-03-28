"""Application module for simulations services simulations scenario generation runtime service workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.simulations.constants.simulations_constants_simulations_blueprints_constants import (
    DEFAULT_5_DAY_BLUEPRINT,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_constants import (
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
from app.simulations.services.simulations_services_simulations_scenario_generation_model import (
    GeneratedScenarioPayload,
    ScenarioGenerationMetadata,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_payloads_service import (
    build_rubric_json,
    build_task_prompts_json,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_story_service import (
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
    pick: PickFn,
    template_display_name: TemplateNameFn,
) -> GeneratedScenarioPayload:
    """Build deterministic template scenario."""
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
    return GeneratedScenarioPayload(
        storyline_md=storyline_md,
        task_prompts_json=task_prompts_json,
        rubric_json=build_rubric_json(role=role, tech_stack=tech_stack),
        metadata=ScenarioGenerationMetadata(
            source=SCENARIO_SOURCE_TEMPLATE_FALLBACK,
            model_name=FALLBACK_MODEL_NAME,
            model_version=FALLBACK_MODEL_VERSION,
            prompt_version=SCENARIO_PROMPT_VERSION,
            rubric_version=SCENARIO_RUBRIC_VERSION,
            template_key=template_key,
        ),
    )


def generate_scenario_payload(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
    choose_source: ChooseSourceFn,
    generate_with_llm: GenerateLlmFn,
    build_fallback: FallbackBuilderFn,
    logger: Any,
) -> GeneratedScenarioPayload:
    """Generate scenario payload."""
    source = choose_source()
    if source == SCENARIO_SOURCE_TEMPLATE_FALLBACK:
        return build_fallback(
            role=role, tech_stack=tech_stack, template_key=template_key
        )
    try:
        return generate_with_llm(
            role=role, tech_stack=tech_stack, template_key=template_key
        )
    except Exception as exc:
        logger.warning(
            "scenario_generation_llm_failed_fallback",
            extra={"templateKey": template_key, "errorType": type(exc).__name__},
        )
        return build_fallback(
            role=role, tech_stack=tech_stack, template_key=template_key
        )


__all__ = ["build_deterministic_template_scenario", "generate_scenario_payload"]
