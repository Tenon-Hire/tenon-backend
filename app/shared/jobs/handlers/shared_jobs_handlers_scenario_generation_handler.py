"""Application module for jobs handlers scenario generation handler workflows."""

from __future__ import annotations

import logging
from typing import Any

from app.shared.database import async_session_maker
from app.shared.jobs.handlers.shared_jobs_handlers_scenario_generation_parse_handler import (
    _parse_positive_int,
)
from app.shared.jobs.handlers.shared_jobs_handlers_scenario_generation_paths_handler import (
    _apply_default_scenario_version,
    _apply_requested_scenario_version,
)
from app.shared.jobs.handlers.shared_jobs_handlers_scenario_generation_runtime_handler import (
    handle_scenario_generation_impl,
)
from app.trials.services.trials_services_trials_lifecycle_service import (
    apply_status_transition,
    normalize_trial_status,
)
from app.trials.services.trials_services_trials_scenario_generation_service import (
    SCENARIO_GENERATION_JOB_TYPE,
    apply_generated_task_updates,
    generate_scenario_payload,
)

logger = logging.getLogger(__name__)


async def handle_scenario_generation(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Handle scenario generation."""
    return await handle_scenario_generation_impl(
        payload_json,
        parse_positive_int=_parse_positive_int,
        async_session_maker=async_session_maker,
        normalize_trial_status=normalize_trial_status,
        generate_scenario_payload=generate_scenario_payload,
        apply_generated_task_updates=apply_generated_task_updates,
        apply_status_transition=apply_status_transition,
        apply_requested_scenario_version=_apply_requested_scenario_version,
        apply_default_scenario_version=_apply_default_scenario_version,
        logger=logger,
    )


__all__ = ["SCENARIO_GENERATION_JOB_TYPE", "handle_scenario_generation"]
