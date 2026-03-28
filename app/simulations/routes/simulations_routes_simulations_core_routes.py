"""Aggregator for simulation routes split into submodules."""

from app.notifications.services import service as notification_service
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.simulations import services as sim_service
from app.simulations.routes.simulations_routes import router
from app.simulations.routes.simulations_routes import (
    simulations_routes_simulations_routes_simulations_routes_rate_limits_routes as rate_limits,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_candidates_compare_routes import (
    list_simulation_candidates_compare,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_candidates_routes import (
    list_simulation_candidates,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_create_routes import (
    create_simulation,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_detail_routes import (
    get_simulation_detail,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_invite_create_routes import (
    create_candidate_invite,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_invite_resend_routes import (
    resend_candidate_invite,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_lifecycle_routes import (
    activate_simulation,
    terminate_simulation,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_list_simulations_routes import (
    list_simulations,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_scenario_routes import (
    approve_scenario_version,
    patch_scenario_version,
    regenerate_scenario_version,
    update_active_scenario_version,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_update_routes import (
    update_simulation,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)

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
    "list_simulation_candidates_compare",
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
