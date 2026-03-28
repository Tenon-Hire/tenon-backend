"""Application module for simulations services simulations scenario generation service workflows."""

from __future__ import annotations

import logging

from app.simulations.services.simulations_services_simulations_scenario_generation_constants import (
    SCENARIO_GENERATION_JOB_TYPE,
    SCENARIO_PROMPT_VERSION,
    SCENARIO_RUBRIC_VERSION,
    SCENARIO_SOURCE_LLM,
    SCENARIO_SOURCE_TEMPLATE_FALLBACK,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_env_service import (
    choose_generation_source,
    is_demo_mode_enabled,
    llm_credentials_available,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_model import (
    GeneratedScenarioPayload,
    ScenarioGenerationMetadata,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_runtime_service import (
    build_deterministic_template_scenario as _build_deterministic_impl,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_runtime_service import (
    generate_scenario_payload as _generate_payload_impl,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_updates_service import (
    apply_generated_task_updates,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    TEMPLATE_CATALOG,
)

logger = logging.getLogger(__name__)


def _pick(options: tuple[str, ...], seed: int, salt: int) -> str:
    if not options:
        return ""
    index = (seed + (salt * 7919)) % len(options)
    return options[index]


def _template_display_name(template_key: str) -> str:
    entry = TEMPLATE_CATALOG.get(template_key)
    if isinstance(entry, dict):
        display_name = entry.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            return display_name.strip()
    return template_key


def build_deterministic_template_scenario(
    *, role: str, tech_stack: str, template_key: str
) -> GeneratedScenarioPayload:
    """Build deterministic template scenario."""
    return _build_deterministic_impl(
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
        pick=_pick,
        template_display_name=_template_display_name,
    )


def _generate_with_llm(
    *, role: str, tech_stack: str, template_key: str
) -> GeneratedScenarioPayload:
    logger.info(
        "scenario_generation_llm_not_implemented",
        extra={"role": role, "techStack": tech_stack, "templateKey": template_key},
    )
    raise RuntimeError("llm_generation_not_implemented")


def generate_scenario_payload(
    *, role: str, tech_stack: str, template_key: str
) -> GeneratedScenarioPayload:
    """Generate scenario payload."""
    return _generate_payload_impl(
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
        choose_source=choose_generation_source,
        generate_with_llm=_generate_with_llm,
        build_fallback=build_deterministic_template_scenario,
        logger=logger,
    )


__all__ = [
    "SCENARIO_GENERATION_JOB_TYPE",
    "SCENARIO_PROMPT_VERSION",
    "SCENARIO_RUBRIC_VERSION",
    "SCENARIO_SOURCE_LLM",
    "SCENARIO_SOURCE_TEMPLATE_FALLBACK",
    "ScenarioGenerationMetadata",
    "GeneratedScenarioPayload",
    "is_demo_mode_enabled",
    "llm_credentials_available",
    "choose_generation_source",
    "build_deterministic_template_scenario",
    "generate_scenario_payload",
    "apply_generated_task_updates",
]
