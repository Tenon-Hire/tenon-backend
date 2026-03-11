from app.jobs import worker
from app.jobs.handlers import (
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    SCENARIO_GENERATION_JOB_TYPE,
    SIMULATION_CLEANUP_JOB_TYPE,
    TRANSCRIBE_RECORDING_JOB_TYPE,
)


def test_register_builtin_handlers_is_explicit():
    worker.clear_handlers()
    try:
        assert worker.has_handler(SIMULATION_CLEANUP_JOB_TYPE) is False
        assert worker.has_handler(DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE) is False
        assert worker.has_handler(DAY_CLOSE_ENFORCEMENT_JOB_TYPE) is False
        assert worker.has_handler(SCENARIO_GENERATION_JOB_TYPE) is False
        assert worker.has_handler(TRANSCRIBE_RECORDING_JOB_TYPE) is False

        worker.register_builtin_handlers()

        assert worker.has_handler(SIMULATION_CLEANUP_JOB_TYPE) is True
        assert worker.has_handler(DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE) is True
        assert worker.has_handler(DAY_CLOSE_ENFORCEMENT_JOB_TYPE) is True
        assert worker.has_handler(SCENARIO_GENERATION_JOB_TYPE) is True
        assert worker.has_handler(TRANSCRIBE_RECORDING_JOB_TYPE) is True
    finally:
        worker.clear_handlers()
