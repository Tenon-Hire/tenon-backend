"""Application module for simulations services simulations scenario versions constants workflows."""

from __future__ import annotations

from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_READY,
)
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
)

SCENARIO_PATCH_ERROR_CODE = "SCENARIO_PATCH_INVALID"
SCENARIO_NOT_EDITABLE_ERROR_CODE = "SCENARIO_NOT_EDITABLE"
ALLOWED_EDITABLE_SIMULATION_STATUSES = frozenset(
    {SIMULATION_STATUS_READY_FOR_REVIEW, SIMULATION_STATUS_ACTIVE_INVITING}
)
ALLOWED_EDITABLE_SCENARIO_STATUSES = frozenset({SCENARIO_VERSION_STATUS_READY})
SCENARIO_PATCH_FIELD_ORDER = (
    "storyline_md",
    "task_prompts_json",
    "rubric_json",
    "focus_notes",
)
SCENARIO_PATCH_DEEP_COPY_FIELDS = frozenset({"task_prompts_json", "rubric_json"})
