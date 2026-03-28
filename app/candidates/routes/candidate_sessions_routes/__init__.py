"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_current_task_logic_routes as current_task_logic,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_current_task_routes as current_task,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_invites_routes as invites,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_privacy_routes as privacy,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_rate_limits_routes as rate_limits,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_resolve_routes as resolve,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_routes as responses,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_schedule_routes as schedule,
)
from . import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_time_utils as time_utils,
)

router = APIRouter()
router.include_router(resolve.router)
router.include_router(schedule.router)
router.include_router(current_task.router)
router.include_router(invites.router)
router.include_router(privacy.router)

__all__ = [
    "current_task",
    "current_task_logic",
    "invites",
    "privacy",
    "rate_limits",
    "resolve",
    "responses",
    "router",
    "schedule",
    "time_utils",
]
