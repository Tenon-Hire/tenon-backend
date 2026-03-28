"""Application module for jobs worker runtime registry service workflows."""

from __future__ import annotations

from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_types_model import (
    JobHandler,
)

_HANDLERS: dict[str, JobHandler] = {}


def _normalize_job_type(job_type: str) -> str:
    return job_type.strip()


def register_handler(job_type: str, handler: JobHandler) -> None:
    """Execute register handler."""
    normalized = _normalize_job_type(job_type)
    if not normalized:
        raise ValueError("job_type is required")
    _HANDLERS[normalized] = handler


def clear_handlers() -> None:
    """Execute clear handlers."""
    _HANDLERS.clear()


def has_handler(job_type: str) -> bool:
    """Execute has handler."""
    normalized = _normalize_job_type(job_type)
    return bool(normalized and normalized in _HANDLERS)


def get_handler(job_type: str) -> JobHandler | None:
    """Return handler."""
    return _HANDLERS.get(job_type)


def register_builtin_handlers() -> None:
    """Execute register builtin handlers."""
    from app.shared.jobs.handlers import (
        DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
        DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
        EVALUATION_RUN_JOB_TYPE,
        GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
        SCENARIO_GENERATION_JOB_TYPE,
        SIMULATION_CLEANUP_JOB_TYPE,
        TRANSCRIBE_RECORDING_JOB_TYPE,
        WORKSPACE_CLEANUP_JOB_TYPE,
        handle_day_close_enforcement,
        handle_day_close_finalize_text,
        handle_evaluation_run,
        handle_github_workflow_artifact_parse,
        handle_scenario_generation,
        handle_simulation_cleanup,
        handle_transcribe_recording,
        handle_workspace_cleanup,
    )

    register_handler(SIMULATION_CLEANUP_JOB_TYPE, handle_simulation_cleanup)
    register_handler(WORKSPACE_CLEANUP_JOB_TYPE, handle_workspace_cleanup)
    register_handler(DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE, handle_day_close_finalize_text)
    register_handler(DAY_CLOSE_ENFORCEMENT_JOB_TYPE, handle_day_close_enforcement)
    register_handler(EVALUATION_RUN_JOB_TYPE, handle_evaluation_run)
    register_handler(
        GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
        handle_github_workflow_artifact_parse,
    )
    register_handler(SCENARIO_GENERATION_JOB_TYPE, handle_scenario_generation)
    register_handler(TRANSCRIBE_RECORDING_JOB_TYPE, handle_transcribe_recording)


__all__ = [
    "clear_handlers",
    "get_handler",
    "has_handler",
    "register_builtin_handlers",
    "register_handler",
]
