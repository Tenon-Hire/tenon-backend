from app.jobs import worker
from app.jobs.handlers import SIMULATION_CLEANUP_JOB_TYPE


def test_register_builtin_handlers_is_explicit():
    worker.clear_handlers()
    try:
        assert worker.has_handler(SIMULATION_CLEANUP_JOB_TYPE) is False

        worker.register_builtin_handlers()

        assert worker.has_handler(SIMULATION_CLEANUP_JOB_TYPE) is True
    finally:
        worker.clear_handlers()
