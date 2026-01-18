"""Aggregated tasks router (codespaces, runs, submissions).

Kept slightly above 50 LOC to preserve legacy import points used by tests while delegating
real routing to app.api.routes.tasks.* modules.
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter

from app.api.dependencies.github_native import get_actions_runner, get_github_client
from app.api.routes.tasks import init as init_route
from app.api.routes.tasks import poll, run, status, submit
from app.api.routes.tasks import router as tasks_router
from app.domains.candidate_sessions import service as cs_service
from app.domains.submissions import rate_limits as _rate_limits
from app.domains.submissions import service_candidate as submission_service
from app.domains.submissions.rate_limits import (
    POLL_MIN_INTERVAL_SECONDS as _POLL_MIN_INTERVAL_SECONDS,
)
from app.domains.submissions.rate_limits import RATE_LIMIT_RULES as _RATE_LIMIT_RULE
from app.domains.submissions.rate_limits import (
    RUN_CONCURRENCY_LIMIT as _RUN_CONCURRENCY_LIMIT,
)
from app.domains.submissions.rate_limits import (
    apply_rate_limit,
)
from app.infra.config import settings
from app.infra.security import rate_limit


def _rate_limit_or_429(candidate_session_id: int, action: str) -> None:
    # Keep legacy mutability for tests that overwrite _RATE_LIMIT_RULE.
    _rate_limits.RATE_LIMIT_RULES.clear()
    _rate_limits.RATE_LIMIT_RULES.update(_RATE_LIMIT_RULE)
    apply_rate_limit(candidate_session_id, action)


@asynccontextmanager
async def _concurrency_guard(key: str, limit: int):
    if not rate_limit.rate_limit_enabled():
        yield
        return
    async with rate_limit.limiter.concurrency_guard(key, limit):
        yield


async def _compute_current_task(db, cs):
    tasks, _, current, *_ = await cs_service.progress_snapshot(db, cs)
    return current


router = APIRouter()
router.include_router(tasks_router)

# Legacy aliases for tests/overrides
init_codespace = init_route.init_codespace_route
codespace_status = status.codespace_status_route
run_task_tests = run.run_task_tests_route
get_run_result = poll.get_run_result_route
submit_task = submit.submit_task_route
workspace_repo = submission_service.workspace_repo

__all__ = [
    "router",
    "get_actions_runner",
    "get_github_client",
    "init_codespace",
    "codespace_status",
    "run_task_tests",
    "get_run_result",
    "submit_task",
    "submission_service",
    "workspace_repo",
    "_rate_limit_or_429",
    "_concurrency_guard",
    "_compute_current_task",
    "_RATE_LIMIT_RULE",
    "_POLL_MIN_INTERVAL_SECONDS",
    "_RUN_CONCURRENCY_LIMIT",
    "settings",
    "rate_limit",
]
