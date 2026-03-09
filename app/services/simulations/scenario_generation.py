from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any

from app.domains.simulations.blueprints import DEFAULT_5_DAY_BLUEPRINT
from app.services.tasks.template_catalog import TEMPLATE_CATALOG

SCENARIO_GENERATION_JOB_TYPE = "scenario_generation"
SCENARIO_PROMPT_VERSION = "scenario-generation-v1"
SCENARIO_RUBRIC_VERSION = "scenario-rubric-v1"
FALLBACK_MODEL_NAME = "template_catalog_fallback"
FALLBACK_MODEL_VERSION = "v1"

SCENARIO_SOURCE_LLM = "llm"
SCENARIO_SOURCE_TEMPLATE_FALLBACK = "template_fallback"

logger = logging.getLogger(__name__)

_OPENAI_API_ENV_KEYS = ("TENON_OPENAI_API_KEY", "OPENAI_API_KEY")
_ANTHROPIC_API_ENV_KEYS = ("TENON_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
_DEMO_MODE_ENV_KEYS = ("TENON_DEMO_MODE", "TENON_SCENARIO_DEMO_MODE")

_STORYLINE_CONTEXTS = (
    "a monetization feature with strict reporting accuracy requirements",
    "an incident-prone integration that needs stronger reliability boundaries",
    "a high-volume workflow where latency spikes directly impact conversion",
    "a migration effort balancing delivery speed and production safety",
    "a compliance-sensitive release with explicit auditability expectations",
)
_STORYLINE_CONSTRAINTS = (
    "tight operational observability from day one",
    "clear rollback paths for every risky change",
    "small, testable increments that can ship safely",
    "explicit failure-mode handling and graceful degradation",
    "well-scoped interfaces so ownership stays clear",
)
_CODE_PRIORITIES = (
    "correctness under realistic edge cases",
    "testability and maintainable abstractions",
    "performance-sensitive database access patterns",
    "defensive validation and error handling",
    "traceable behavior with useful diagnostics",
)
_DEBUG_SIGNALS = (
    "a flaky production-like test signal",
    "an intermittent regression after a recent refactor",
    "inconsistent behavior across environments",
    "a correctness bug hidden by shallow happy-path tests",
    "a state-management bug triggered by retry paths",
)


@dataclass(slots=True, frozen=True)
class ScenarioGenerationMetadata:
    source: str
    model_name: str | None
    model_version: str | None
    prompt_version: str
    rubric_version: str
    template_key: str


@dataclass(slots=True, frozen=True)
class GeneratedScenarioPayload:
    storyline_md: str
    task_prompts_json: list[dict[str, Any]]
    rubric_json: dict[str, Any]
    metadata: ScenarioGenerationMetadata


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _truthy_env(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _has_any_env(keys: tuple[str, ...]) -> bool:
    return any((os.getenv(key) or "").strip() for key in keys)


def is_demo_mode_enabled() -> bool:
    return any(_truthy_env(os.getenv(key)) for key in _DEMO_MODE_ENV_KEYS)


def llm_credentials_available() -> bool:
    return _has_any_env(_OPENAI_API_ENV_KEYS + _ANTHROPIC_API_ENV_KEYS)


def choose_generation_source(
    *,
    demo_mode_enabled: bool | None = None,
    llm_available: bool | None = None,
) -> str:
    if demo_mode_enabled is None:
        demo_mode_enabled = is_demo_mode_enabled()
    if demo_mode_enabled:
        return SCENARIO_SOURCE_TEMPLATE_FALLBACK
    if llm_available is None:
        llm_available = llm_credentials_available()
    if not llm_available:
        return SCENARIO_SOURCE_TEMPLATE_FALLBACK
    return SCENARIO_SOURCE_LLM


def _seed_from_inputs(role: str, tech_stack: str, template_key: str) -> int:
    seed_source = "||".join(
        (
            _normalize_text(role).lower(),
            _normalize_text(tech_stack).lower(),
            _normalize_text(template_key).lower(),
        )
    )
    digest = hashlib.sha256(seed_source.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _pick(options: tuple[str, ...], *, seed: int, salt: int) -> str:
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


def _build_storyline_markdown(*, role: str, tech_stack: str, template_key: str) -> str:
    seed = _seed_from_inputs(role, tech_stack, template_key)
    display_name = _template_display_name(template_key)
    context = _pick(_STORYLINE_CONTEXTS, seed=seed, salt=1)
    constraint = _pick(_STORYLINE_CONSTRAINTS, seed=seed, salt=2)

    role_label = _normalize_text(role) or "Software Engineer"
    stack_label = _normalize_text(tech_stack) or "general backend stack"

    return "\n".join(
        [
            f"# {role_label} Scenario v1",
            "",
            f"You are joining a product team shipping services on **{stack_label}**.",
            (
                f"The repository baseline uses the **{display_name}** template and "
                f"the team is currently working on {context}."
            ),
            (
                "Your mandate is to deliver a safe, production-quality increment with "
                f"{constraint} while keeping communication clear for reviewers."
            ),
        ]
    )


def _build_task_description(
    *,
    day_index: int,
    role: str,
    tech_stack: str,
    template_key: str,
) -> str:
    seed = _seed_from_inputs(role, tech_stack, template_key)
    priority = _pick(_CODE_PRIORITIES, seed=seed, salt=10 + day_index)
    debug_signal = _pick(_DEBUG_SIGNALS, seed=seed, salt=20 + day_index)

    stack_label = _normalize_text(tech_stack) or "the target stack"
    template_name = _template_display_name(template_key)

    if day_index == 1:
        return (
            "Draft an implementation plan that defines service boundaries, key data "
            "flows, API contracts, and risk controls. Include concrete tradeoffs and "
            f"how you will validate correctness in {stack_label}."
        )
    if day_index == 2:
        return (
            "Implement the primary backend slice in code with tests. Prioritize "
            f"{priority} and keep the solution aligned with the {template_name} "
            "project structure."
        )
    if day_index == 3:
        return (
            "Investigate and fix a failing behavior path. Treat "
            f"{debug_signal} as the anchor signal, isolate root cause, and add "
            "regression coverage."
        )
    if day_index == 4:
        return (
            "Refactor for maintainability and handoff quality. Leave clear comments, "
            "reduce cognitive load, and document operational implications of your "
            "changes."
        )
    return (
        "Write a structured engineering reflection covering decisions, tradeoffs, "
        "risk handling, and what you would improve with one additional iteration."
    )


def _build_task_prompts_json(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
) -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []
    for blueprint in sorted(
        DEFAULT_5_DAY_BLUEPRINT, key=lambda item: item["day_index"]
    ):
        day_index = int(blueprint["day_index"])
        prompts.append(
            {
                "dayIndex": day_index,
                "type": blueprint["type"],
                "title": blueprint["title"],
                "description": _build_task_description(
                    day_index=day_index,
                    role=role,
                    tech_stack=tech_stack,
                    template_key=template_key,
                ),
            }
        )
    return prompts


def _build_rubric_json(*, role: str, tech_stack: str) -> dict[str, Any]:
    role_label = _normalize_text(role) or "Engineer"
    stack_label = _normalize_text(tech_stack) or "target stack"
    return {
        "summary": (
            f"Evaluate {role_label} performance across planning, implementation, "
            f"debugging, handoff, and reflection in {stack_label}."
        ),
        "dayWeights": {"1": 20, "2": 30, "3": 25, "4": 15, "5": 10},
        "dimensions": [
            {
                "name": "Problem framing",
                "weight": 25,
                "description": "Defines scope, constraints, and execution plan clearly.",
            },
            {
                "name": "Technical execution",
                "weight": 35,
                "description": "Ships correct, maintainable changes with useful tests.",
            },
            {
                "name": "Debugging rigor",
                "weight": 20,
                "description": "Finds root cause methodically and verifies the fix.",
            },
            {
                "name": "Communication and handoff",
                "weight": 20,
                "description": "Documents decisions, risks, and clear next steps.",
            },
        ],
    }


def build_deterministic_template_scenario(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
) -> GeneratedScenarioPayload:
    storyline_md = _build_storyline_markdown(
        role=role, tech_stack=tech_stack, template_key=template_key
    )
    task_prompts_json = _build_task_prompts_json(
        role=role, tech_stack=tech_stack, template_key=template_key
    )
    rubric_json = _build_rubric_json(role=role, tech_stack=tech_stack)
    return GeneratedScenarioPayload(
        storyline_md=storyline_md,
        task_prompts_json=task_prompts_json,
        rubric_json=rubric_json,
        metadata=ScenarioGenerationMetadata(
            source=SCENARIO_SOURCE_TEMPLATE_FALLBACK,
            model_name=FALLBACK_MODEL_NAME,
            model_version=FALLBACK_MODEL_VERSION,
            prompt_version=SCENARIO_PROMPT_VERSION,
            rubric_version=SCENARIO_RUBRIC_VERSION,
            template_key=template_key,
        ),
    )


def _generate_with_llm(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
) -> GeneratedScenarioPayload:
    logger.info(
        "scenario_generation_llm_not_implemented",
        extra={
            "role": role,
            "techStack": tech_stack,
            "templateKey": template_key,
        },
    )
    raise RuntimeError("llm_generation_not_implemented")


def _build_template_fallback_payload(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
) -> GeneratedScenarioPayload:
    return build_deterministic_template_scenario(
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
    )


def generate_scenario_payload(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
) -> GeneratedScenarioPayload:
    source = choose_generation_source()
    if source == SCENARIO_SOURCE_TEMPLATE_FALLBACK:
        return _build_template_fallback_payload(
            role=role,
            tech_stack=tech_stack,
            template_key=template_key,
        )

    try:
        return _generate_with_llm(
            role=role,
            tech_stack=tech_stack,
            template_key=template_key,
        )
    except Exception as exc:
        logger.warning(
            "scenario_generation_llm_failed_fallback",
            extra={
                "templateKey": template_key,
                "errorType": type(exc).__name__,
            },
        )
    return _build_template_fallback_payload(
        role=role,
        tech_stack=tech_stack,
        template_key=template_key,
    )


def apply_generated_task_updates(
    *,
    tasks: list[Any],
    task_prompts_json: list[dict[str, Any]],
    rubric_json: dict[str, Any],
) -> None:
    prompts_by_day: dict[int, dict[str, Any]] = {}
    for prompt in task_prompts_json:
        raw_day = prompt.get("dayIndex")
        if isinstance(raw_day, int) and raw_day > 0:
            prompts_by_day[raw_day] = prompt

    parsed_weights: dict[int, int] = {}
    raw_weights = rubric_json.get("dayWeights")
    if isinstance(raw_weights, dict):
        for raw_day, raw_weight in raw_weights.items():
            try:
                day_index = int(str(raw_day))
                weight = int(raw_weight)
            except (TypeError, ValueError):
                continue
            if day_index > 0 and weight > 0:
                parsed_weights[day_index] = weight

    for task in tasks:
        prompt = prompts_by_day.get(getattr(task, "day_index", -1))
        if isinstance(prompt, dict):
            description = prompt.get("description")
            title = prompt.get("title")
            if isinstance(description, str) and description.strip():
                task.description = description.strip()
            if isinstance(title, str) and title.strip():
                task.title = title.strip()

        weight = parsed_weights.get(getattr(task, "day_index", -1))
        if weight is not None:
            task.max_score = weight


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
