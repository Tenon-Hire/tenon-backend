"""Application module for trials services trials scenario versions validation task prompts service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.trials.schemas.trials_schemas_trials_core_schema import (
    MAX_SCENARIO_TASK_PROMPTS_BYTES,
)
from app.trials.services.trials_services_trials_scenario_versions_validation_base_service import (
    json_payload_size_bytes,
    parse_positive_int,
    raise_patch_validation_error,
)


def validate_task_prompts(task_prompts_json: Any) -> list[dict[str, Any]]:
    """Validate task prompts."""
    if not isinstance(task_prompts_json, list):
        raise_patch_validation_error(
            "taskPrompts must be an array.",
            field="taskPrompts",
        )
    size_bytes = json_payload_size_bytes(task_prompts_json)
    if size_bytes > MAX_SCENARIO_TASK_PROMPTS_BYTES:
        raise_patch_validation_error(
            f"taskPrompts exceeds {MAX_SCENARIO_TASK_PROMPTS_BYTES} bytes.",
            field="taskPrompts",
            details={
                "maxBytes": MAX_SCENARIO_TASK_PROMPTS_BYTES,
                "actualBytes": size_bytes,
            },
        )
    seen_day_indices: set[int] = set()
    normalized: list[dict[str, Any]] = []
    for index, prompt in enumerate(task_prompts_json):
        if not isinstance(prompt, Mapping):
            raise_patch_validation_error(
                "Each taskPrompts item must be an object.",
                field="taskPrompts",
                details={"index": index},
            )
        normalized_prompt = dict(prompt)
        day_index = parse_positive_int(normalized_prompt.get("dayIndex"))
        if day_index is None or day_index in seen_day_indices:
            detail = (
                "Each taskPrompts item must include a positive integer dayIndex."
                if day_index is None
                else "taskPrompts contains duplicate dayIndex values."
            )
            details = {"index": index} if day_index is None else {"dayIndex": day_index}
            raise_patch_validation_error(detail, field="taskPrompts", details=details)
        seen_day_indices.add(day_index)
        _validate_prompt_text(normalized_prompt.get("title"), "title", index)
        _validate_prompt_text(
            normalized_prompt.get("description"), "description", index
        )
        normalized_prompt["dayIndex"] = day_index
        normalized_prompt["title"] = normalized_prompt["title"].strip()
        normalized_prompt["description"] = normalized_prompt["description"].strip()
        type_value = normalized_prompt.get("type")
        if type_value is not None:
            _validate_prompt_text(type_value, "type", index)
            normalized_prompt["type"] = type_value.strip()
        normalized.append(normalized_prompt)
    return normalized


def _validate_prompt_text(value: Any, field_name: str, index: int) -> None:
    if isinstance(value, str) and value.strip():
        return
    message = (
        f"Each taskPrompts item must include a non-empty {field_name}."
        if field_name != "type"
        else "taskPrompts type must be a non-empty string when provided."
    )
    raise_patch_validation_error(
        message,
        field="taskPrompts",
        details={"index": index},
    )
