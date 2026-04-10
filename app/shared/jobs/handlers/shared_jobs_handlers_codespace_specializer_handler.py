"""Application module for jobs handlers codespace specializer workflows."""

from __future__ import annotations

from typing import Any

from app.shared.database import async_session_maker
from app.trials.services.trials_services_trials_codespace_specializer_service import (
    CODESPACE_SPECIALIZER_JOB_TYPE,
    run_codespace_specializer_job,
)


def _parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


async def handle_codespace_specializer(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Handle codespace-specializer execution."""
    trial_id = _parse_positive_int(payload_json.get("trialId"))
    scenario_version_id = _parse_positive_int(payload_json.get("scenarioVersionId"))
    if trial_id is None or scenario_version_id is None:
        return {
            "status": "skipped_invalid_payload",
            "trialId": trial_id,
            "scenarioVersionId": scenario_version_id,
        }
    async with async_session_maker() as db:
        return await run_codespace_specializer_job(
            db,
            trial_id=trial_id,
            scenario_version_id=scenario_version_id,
        )


__all__ = ["CODESPACE_SPECIALIZER_JOB_TYPE", "handle_codespace_specializer"]
