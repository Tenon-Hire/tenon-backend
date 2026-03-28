"""Application module for simulations routes simulations routes simulations routes scenario payloads routes workflows."""

from __future__ import annotations

from typing import Any

from app.simulations import services as sim_service
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    ScenarioActiveUpdateResponse,
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioStateSummary,
    ScenarioVersionPatchResponse,
)

_ACTIVE_UPDATE_FIELD_MAP = {
    "storylineMd": "storyline_md",
    "taskPromptsJson": "task_prompts_json",
    "rubricJson": "rubric_json",
    "focusNotes": "focus_notes",
    "status": "status",
}
_PATCH_UPDATE_FIELD_MAP = {
    "storylineMd": "storyline_md",
    "taskPrompts": "task_prompts_json",
    "rubric": "rubric_json",
    "notes": "focus_notes",
}


def build_scenario_state_summary(scenario_version: Any) -> ScenarioStateSummary:
    """Build scenario state summary."""
    return ScenarioStateSummary(
        id=scenario_version.id,
        versionIndex=scenario_version.version_index,
        status=scenario_version.status,
        lockedAt=scenario_version.locked_at,
    )


def build_regenerate_response(
    scenario_version: Any,
    scenario_job: Any,
) -> ScenarioRegenerateResponse:
    """Build regenerate response."""
    return ScenarioRegenerateResponse(
        scenarioVersionId=scenario_version.id,
        jobId=scenario_job.id,
        status=scenario_version.status,
    )


def build_approve_response(
    simulation: Any, scenario_version: Any
) -> ScenarioApproveResponse:
    """Build approve response."""
    return ScenarioApproveResponse(
        simulationId=simulation.id,
        status=sim_service.normalize_simulation_status_or_raise(simulation.status),
        activeScenarioVersionId=simulation.active_scenario_version_id
        or scenario_version.id,
        pendingScenarioVersionId=simulation.pending_scenario_version_id,
        scenario=build_scenario_state_summary(scenario_version),
    )


def build_active_update_response(
    simulation_id: int,
    scenario_version: Any,
) -> ScenarioActiveUpdateResponse:
    """Build active update response."""
    return ScenarioActiveUpdateResponse(
        simulationId=simulation_id,
        scenario=build_scenario_state_summary(scenario_version),
    )


def build_patch_response(scenario_version: Any) -> ScenarioVersionPatchResponse:
    """Build patch response."""
    return ScenarioVersionPatchResponse(
        scenarioVersionId=scenario_version.id,
        status=scenario_version.status,
    )


def normalize_active_updates(payload: Any) -> dict[str, Any]:
    """Normalize active updates."""
    updates = payload.model_dump(exclude_unset=True)
    return {
        mapped_name: updates[field_name]
        for field_name, mapped_name in _ACTIVE_UPDATE_FIELD_MAP.items()
        if field_name in updates
    }


def normalize_patch_updates(payload: Any) -> dict[str, Any]:
    """Normalize patch updates."""
    updates = payload.model_dump(exclude_unset=True, exclude_none=False)
    return {
        mapped_name: updates[field_name]
        for field_name, mapped_name in _PATCH_UPDATE_FIELD_MAP.items()
        if field_name in updates
    }
