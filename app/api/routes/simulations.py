"""Aggregator for simulation routes split into submodules."""

from app.api.routes.simulations_routes import router
from app.api.routes.simulations_routes.candidates import list_simulation_candidates
from app.api.routes.simulations_routes.create import create_simulation
from app.api.routes.simulations_routes.detail import get_simulation_detail
from app.api.routes.simulations_routes.invite_create import create_candidate_invite
from app.api.routes.simulations_routes.invite_resend import resend_candidate_invite
from app.api.routes.simulations_routes.list_simulations import list_simulations
from app.domains.notifications import service as notification_service
from app.domains.submissions import service_candidate as submission_service

__all__ = [
    "router",
    "create_candidate_invite",
    "resend_candidate_invite",
    "create_simulation",
    "get_simulation_detail",
    "list_simulation_candidates",
    "list_simulations",
    "notification_service",
    "submission_service",
]

