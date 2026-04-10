"""Aggregator for trial routes split into submodules."""

from app.notifications.services import service as notification_service
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner_or_none
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.trials import services as sim_service
from app.trials.routes.trials_routes import router
from app.trials.routes.trials_routes import (
    trials_routes_trials_routes_trials_routes_rate_limits_routes as rate_limits,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_candidates_compare_routes import (
    list_trial_candidates_compare,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_candidates_routes import (
    list_trial_candidates,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_create_routes import (
    create_trial,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_detail_routes import (
    get_trial_detail,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_invite_create_routes import (
    create_candidate_invite,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_invite_resend_routes import (
    resend_candidate_invite,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_lifecycle_routes import (
    activate_trial,
    terminate_trial,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_list_trials_routes import (
    list_trials,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_scenario_routes import (
    approve_scenario_version,
    patch_scenario_version,
    regenerate_scenario_version,
    update_active_scenario_version,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_update_routes import (
    update_trial,
)

INVITE_CREATE_RATE_LIMIT = rate_limits.INVITE_CREATE_RATE_LIMIT
INVITE_RESEND_RATE_LIMIT = rate_limits.INVITE_RESEND_RATE_LIMIT
SCENARIO_REGENERATE_RATE_LIMIT = rate_limits.SCENARIO_REGENERATE_RATE_LIMIT
rate_limit = rate_limits.rate_limit

__all__ = [
    "router",
    "create_candidate_invite",
    "resend_candidate_invite",
    "create_trial",
    "update_trial",
    "get_trial_detail",
    "activate_trial",
    "terminate_trial",
    "list_trial_candidates",
    "list_trial_candidates_compare",
    "list_trials",
    "approve_scenario_version",
    "patch_scenario_version",
    "regenerate_scenario_version",
    "update_active_scenario_version",
    "notification_service",
    "submission_service",
    "sim_service",
    "ensure_talent_partner_or_none",
    "rate_limit",
    "INVITE_CREATE_RATE_LIMIT",
    "INVITE_RESEND_RATE_LIMIT",
    "SCENARIO_REGENERATE_RATE_LIMIT",
]
