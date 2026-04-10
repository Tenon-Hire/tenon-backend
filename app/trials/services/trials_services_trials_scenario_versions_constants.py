"""Application module for trials services trials scenario versions constants workflows."""

from __future__ import annotations

from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_READY,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_ACTIVE_INVITING,
    TRIAL_STATUS_READY_FOR_REVIEW,
)

SCENARIO_PATCH_ERROR_CODE = "SCENARIO_PATCH_INVALID"
SCENARIO_NOT_EDITABLE_ERROR_CODE = "SCENARIO_NOT_EDITABLE"
ALLOWED_EDITABLE_TRIAL_STATUSES = frozenset(
    {TRIAL_STATUS_READY_FOR_REVIEW, TRIAL_STATUS_ACTIVE_INVITING}
)
ALLOWED_EDITABLE_SCENARIO_STATUSES = frozenset({SCENARIO_VERSION_STATUS_READY})
SCENARIO_PATCH_FIELD_ORDER = (
    "storyline_md",
    "task_prompts_json",
    "rubric_json",
    "focus_notes",
)
SCENARIO_PATCH_DEEP_COPY_FIELDS = frozenset({"task_prompts_json", "rubric_json"})
