"""Aggregator for candidate session routes split into submodules."""

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.routes.candidate_sessions_routes import (
    candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_rate_limits_routes as rate_limits,
)
from app.candidates.routes.candidate_sessions_routes import router
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_current_task_routes import (
    get_current_task,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_invites_routes import (
    list_candidate_invites,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_privacy_routes import (
    record_candidate_privacy_consent,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_resolve_routes import (
    claim_candidate_session,
    resolve_candidate_session,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_schedule_routes import (
    schedule_candidate_session,
)

CANDIDATE_CLAIM_RATE_LIMIT = rate_limits.CANDIDATE_CLAIM_RATE_LIMIT
rate_limit = rate_limits.rate_limit

__all__ = [
    "router",
    "cs_service",
    "resolve_candidate_session",
    "claim_candidate_session",
    "schedule_candidate_session",
    "get_current_task",
    "list_candidate_invites",
    "record_candidate_privacy_consent",
    "rate_limit",
    "CANDIDATE_CLAIM_RATE_LIMIT",
]
