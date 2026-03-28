"""Application module for simulations services simulations scenario versions patching service workflows."""

from __future__ import annotations

import copy
from typing import Any

from app.simulations.services.simulations_services_simulations_scenario_versions_constants import (
    ALLOWED_EDITABLE_SCENARIO_STATUSES,
    ALLOWED_EDITABLE_SIMULATION_STATUSES,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_validation_base_service import (
    validate_notes,
    validate_storyline,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_validation_rubric_service import (
    validate_rubric,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_validation_task_prompts_service import (
    validate_task_prompts,
)


def is_editable_scenario_status(status_value: str | None) -> bool:
    """Return whether editable scenario status."""
    return status_value in ALLOWED_EDITABLE_SCENARIO_STATUSES


def is_editable_simulation_status(status_value: str | None) -> bool:
    """Return whether editable simulation status."""
    return status_value in ALLOWED_EDITABLE_SIMULATION_STATUSES


def validate_and_normalize_merged_scenario_state(
    merged_state: dict[str, Any],
) -> dict[str, Any]:
    """Validate and normalize merged scenario state."""
    return {
        "storyline_md": validate_storyline(merged_state.get("storyline_md")),
        "task_prompts_json": validate_task_prompts(
            merged_state.get("task_prompts_json")
        ),
        "rubric_json": validate_rubric(merged_state.get("rubric_json")),
        "focus_notes": validate_notes(merged_state.get("focus_notes")),
    }


def build_edit_audit_payload(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    candidate_fields: list[str],
) -> dict[str, Any]:
    """Build edit audit payload."""
    changed_fields: list[str] = []
    before_subset: dict[str, Any] = {}
    after_subset: dict[str, Any] = {}
    for field_name in candidate_fields:
        before_value = before.get(field_name)
        after_value = after.get(field_name)
        if before_value == after_value:
            continue
        changed_fields.append(field_name)
        before_subset[field_name] = copy.deepcopy(before_value)
        after_subset[field_name] = copy.deepcopy(after_value)
    return {
        "changedFields": changed_fields,
        "before": before_subset,
        "after": after_subset,
    }
