from app.core.settings import settings
from app.domains.simulations.blueprints import DEFAULT_5_DAY_BLUEPRINT
from app.repositories.candidate_sessions import repository as cs_repo
from app.repositories.simulations import repository as sim_repo
from app.repositories.simulations.simulation import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_DRAFT,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
)
from app.services.tasks.template_catalog import resolve_template_repo_full_name

from .cleanup_jobs import (
    SIMULATION_CLEANUP_JOB_TYPE,
    build_simulation_cleanup_payload,
    enqueue_simulation_cleanup_job,
    simulation_cleanup_idempotency_key,
)
from .creation import create_simulation_with_tasks
from .invite_create import create_invite
from .invite_errors import InviteRejectedError
from .invite_tokens import _invite_is_expired, _refresh_invite_token
from .invites import create_or_resend_invite
from .lifecycle import (
    TerminateSimulationResult,
    activate_simulation,
    apply_status_transition,
    normalize_simulation_status,
    normalize_simulation_status_or_raise,
    require_owner_for_lifecycle,
    require_simulation_invitable,
    terminate_simulation,
    terminate_simulation_with_cleanup,
)
from .listing import list_candidates_with_profile, list_simulations
from .ownership import require_owned_simulation, require_owned_simulation_with_tasks
from .scenario_payload_builder import build_scenario_generation_payload
from .task_templates import _template_repo_for_task
from .template_keys import ApiError
from .urls import invite_url

__all__ = [
    "ApiError",
    "DEFAULT_5_DAY_BLUEPRINT",
    "InviteRejectedError",
    "SIMULATION_STATUS_ACTIVE_INVITING",
    "SIMULATION_STATUS_DRAFT",
    "SIMULATION_STATUS_GENERATING",
    "SIMULATION_STATUS_READY_FOR_REVIEW",
    "SIMULATION_STATUS_TERMINATED",
    "SIMULATION_CLEANUP_JOB_TYPE",
    "_invite_is_expired",
    "_refresh_invite_token",
    "_template_repo_for_task",
    "TerminateSimulationResult",
    "activate_simulation",
    "apply_status_transition",
    "build_simulation_cleanup_payload",
    "build_scenario_generation_payload",
    "create_invite",
    "create_or_resend_invite",
    "create_simulation_with_tasks",
    "cs_repo",
    "enqueue_simulation_cleanup_job",
    "invite_url",
    "list_candidates_with_profile",
    "list_simulations",
    "normalize_simulation_status",
    "normalize_simulation_status_or_raise",
    "require_owner_for_lifecycle",
    "require_owned_simulation",
    "require_owned_simulation_with_tasks",
    "require_simulation_invitable",
    "resolve_template_repo_full_name",
    "settings",
    "sim_repo",
    "simulation_cleanup_idempotency_key",
    "terminate_simulation",
    "terminate_simulation_with_cleanup",
]
