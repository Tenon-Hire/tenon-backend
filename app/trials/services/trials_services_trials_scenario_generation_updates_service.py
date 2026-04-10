"""Application module for trials services trials scenario generation updates service workflows."""

from __future__ import annotations

from typing import Any


def apply_generated_task_updates(
    *,
    tasks: list[Any],
    task_prompts_json: list[dict[str, Any]],
    rubric_json: dict[str, Any],
) -> None:
    """Apply generated task updates."""
    prompts_by_day = {
        int(prompt["dayIndex"]): prompt
        for prompt in task_prompts_json
        if isinstance(prompt.get("dayIndex"), int) and int(prompt["dayIndex"]) > 0
    }
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


__all__ = ["apply_generated_task_updates"]
