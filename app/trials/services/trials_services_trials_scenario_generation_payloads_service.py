"""Application module for trials services trials scenario generation payloads service workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.trials.services.trials_services_trials_scenario_generation_text_service import (
    normalize_text,
)

TaskDescriptionBuilder = Callable[[int, str, str, str], str]


def build_task_prompts_json(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
    day_blueprint: list[dict[str, Any]],
    task_description_builder: TaskDescriptionBuilder,
) -> list[dict[str, Any]]:
    """Build task prompts json."""
    prompts: list[dict[str, Any]] = []
    for blueprint in sorted(day_blueprint, key=lambda item: item["day_index"]):
        day_index = int(blueprint["day_index"])
        prompts.append(
            {
                "dayIndex": day_index,
                "type": blueprint["type"],
                "title": blueprint["title"],
                "description": task_description_builder(
                    day_index,
                    role,
                    tech_stack,
                    template_key,
                ),
            }
        )
    return prompts


def build_rubric_json(*, role: str) -> dict[str, Any]:
    """Build rubric json."""
    role_label = normalize_text(role) or "Engineer"
    return {
        "summary": f"Evaluate {role_label} performance across planning, implementation, wrap-up, demo presentation, and reflection in a from-scratch build.",
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
                "name": "Implementation completeness and handoff readiness",
                "weight": 20,
                "description": "Finishes the core implementation, hardens edge cases, and leaves the codebase ready for reviewer handoff.",
            },
            {
                "name": "Communication and presentation",
                "weight": 20,
                "description": "Explains decisions, risks, outcomes, and next steps clearly.",
            },
        ],
    }


__all__ = ["build_rubric_json", "build_task_prompts_json"]
