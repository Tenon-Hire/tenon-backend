"""Application module for jobs handlers evaluation run handler workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.services import fit_profile_pipeline
from app.evaluations.services.evaluations_services_evaluations_fit_profile_jobs_service import (
    EVALUATION_RUN_JOB_TYPE,
)
from app.shared.database import async_session_maker


async def handle_evaluation_run(payload_json: dict[str, Any]) -> dict[str, Any]:
    # Imported here to avoid import cycle during worker handler registration.
    """Handle evaluation run."""
    from app.shared.jobs.shared_jobs_worker_service import PermanentJobError

    fit_profile_pipeline.async_session_maker = async_session_maker
    result = await fit_profile_pipeline.process_evaluation_run_job(payload_json)
    if result.get("status") == "failed":
        raise PermanentJobError("evaluation_run_failed")
    return result


__all__ = ["EVALUATION_RUN_JOB_TYPE", "handle_evaluation_run"]
