import pytest

from app.shared.jobs import worker
from app.shared.jobs.handlers import (
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    EVALUATION_RUN_JOB_TYPE,
    GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
    SCENARIO_GENERATION_JOB_TYPE,
    SIMULATION_CLEANUP_JOB_TYPE,
    TRANSCRIBE_RECORDING_JOB_TYPE,
    WORKSPACE_CLEANUP_JOB_TYPE,
)


def test_register_builtin_handlers_is_explicit():
    worker.clear_handlers()
    try:
        assert worker.has_handler(SIMULATION_CLEANUP_JOB_TYPE) is False
        assert worker.has_handler(WORKSPACE_CLEANUP_JOB_TYPE) is False
        assert worker.has_handler(DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE) is False
        assert worker.has_handler(DAY_CLOSE_ENFORCEMENT_JOB_TYPE) is False
        assert worker.has_handler(EVALUATION_RUN_JOB_TYPE) is False
        assert worker.has_handler(GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE) is False
        assert worker.has_handler(SCENARIO_GENERATION_JOB_TYPE) is False
        assert worker.has_handler(TRANSCRIBE_RECORDING_JOB_TYPE) is False

        worker.register_builtin_handlers()

        assert worker.has_handler(SIMULATION_CLEANUP_JOB_TYPE) is True
        assert worker.has_handler(WORKSPACE_CLEANUP_JOB_TYPE) is True
        assert worker.has_handler(DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE) is True
        assert worker.has_handler(DAY_CLOSE_ENFORCEMENT_JOB_TYPE) is True
        assert worker.has_handler(EVALUATION_RUN_JOB_TYPE) is True
        assert worker.has_handler(GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE) is True
        assert worker.has_handler(SCENARIO_GENERATION_JOB_TYPE) is True
        assert worker.has_handler(TRANSCRIBE_RECORDING_JOB_TYPE) is True
    finally:
        worker.clear_handlers()


def test_register_handler_rejects_blank_job_type():
    with pytest.raises(ValueError, match="job_type is required"):
        worker.register_handler("   ", lambda _payload: None)
