"""Aggregated tasks router (codespaces, runs, submissions)."""

from fastapi import APIRouter

from app.candidates.candidate_sessions import services as cs_service
from app.config import settings
from app.shared.auth import rate_limit
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_actions_runner,
    get_github_client,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services import (
    submissions_services_submissions_rate_limits_constants as submissions_rate_limits,
)
from app.tasks.routes.tasks import router as tasks_router
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_codespace_init_routes as tasks_codespace_init_routes,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_codespace_status_routes as tasks_codespace_status_routes,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_run_poll_routes as tasks_run_poll_routes,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_run_routes as tasks_run_routes,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_submit_routes as tasks_submit_routes,
)
from app.tasks.routes.tasks.tasks_routes_tasks_tasks_runtime_utils import (
    _compute_current_task,
    _concurrency_guard,
    _rate_limit_or_429,
)

router = APIRouter()
router.include_router(tasks_router)

# Legacy aliases for tests/overrides
init_codespace = tasks_codespace_init_routes.init_codespace_route
codespace_status = tasks_codespace_status_routes.codespace_status_route
run_task_tests = tasks_run_routes.run_task_tests_route
get_run_result = tasks_run_poll_routes.get_run_result_route
submit_task = tasks_submit_routes.submit_task_route
workspace_repo = submission_service.workspace_repo
_RATE_LIMIT_RULE = submissions_rate_limits._DEFAULT_RATE_LIMIT_RULES

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
    "cs_service",
    "_rate_limit_or_429",
    "_concurrency_guard",
    "_compute_current_task",
    "settings",
    "rate_limit",
    "_RATE_LIMIT_RULE",
]
