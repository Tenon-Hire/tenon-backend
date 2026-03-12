"""Aggregator for simulation routes split into submodules."""

from app.api.routers.simulations_routes import rate_limits, router
from app.api.routers.simulations_routes.candidates import list_simulation_candidates
from app.api.routers.simulations_routes.create import create_simulation
from app.api.routers.simulations_routes.detail import get_simulation_detail
from app.api.routers.simulations_routes.invite_create import create_candidate_invite
from app.api.routers.simulations_routes.invite_resend import resend_candidate_invite
from app.api.routers.simulations_routes.lifecycle import (
    activate_simulation,
    terminate_simulation,
)
from app.api.routers.simulations_routes.list_simulations import list_simulations
from app.api.routers.simulations_routes.scenario import (
    approve_scenario_version,
    patch_scenario_version,
    regenerate_scenario_version,
    update_active_scenario_version,
)
from app.api.routers.simulations_routes.update import update_simulation
from app.core.auth.roles import ensure_recruiter_or_none
from app.domains.notifications import service as notification_service
from app.domains.simulations import service as sim_service
from app.domains.submissions import service_candidate as submission_service

INVITE_CREATE_RATE_LIMIT = rate_limits.INVITE_CREATE_RATE_LIMIT
INVITE_RESEND_RATE_LIMIT = rate_limits.INVITE_RESEND_RATE_LIMIT
SCENARIO_REGENERATE_RATE_LIMIT = rate_limits.SCENARIO_REGENERATE_RATE_LIMIT
rate_limit = rate_limits.rate_limit

__all__ = [
    "router",
    "create_candidate_invite",
    "resend_candidate_invite",
    "create_simulation",
    "update_simulation",
    "get_simulation_detail",
    "activate_simulation",
    "terminate_simulation",
    "list_simulation_candidates",
    "list_simulations",
    "approve_scenario_version",
    "patch_scenario_version",
    "regenerate_scenario_version",
    "update_active_scenario_version",
    "notification_service",
    "submission_service",
    "sim_service",
    "ensure_recruiter_or_none",
    "rate_limit",
    "INVITE_CREATE_RATE_LIMIT",
    "INVITE_RESEND_RATE_LIMIT",
    "SCENARIO_REGENERATE_RATE_LIMIT",
]
