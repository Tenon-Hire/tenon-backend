"""Application module for init workflows."""

from __future__ import annotations

from importlib import import_module

from . import (
    simulations_services_simulations_candidates_compare_service as candidates_compare,
)
from . import simulations_services_simulations_creation_service as creation
from . import simulations_services_simulations_invite_factory_service as invite_factory
from . import (
    simulations_services_simulations_invite_preprovision_service as invite_preprovision,
)
from . import (
    simulations_services_simulations_invite_workflow_service as invite_workflow,
)
from . import simulations_services_simulations_lifecycle_service as lifecycle
from . import (
    simulations_services_simulations_scenario_generation_service as scenario_generation,
)
from . import (
    simulations_services_simulations_scenario_payload_builder_service as scenario_payload_builder,
)
from . import (
    simulations_services_simulations_scenario_versions_service as scenario_versions,
)
from . import simulations_services_simulations_task_templates_service as task_templates
from . import simulations_services_simulations_update_service as update
from .simulations_services_simulations_exports_service import SIMULATIONS_EXPORTS

_SYMBOL_ALIASES: dict[str, tuple[str, str]] = {
    "ApiError": ("app.shared.utils.shared_utils_errors_utils", "ApiError"),
    "DEFAULT_5_DAY_BLUEPRINT": (
        "app.simulations.constants.simulations_constants_simulations_blueprints_constants",
        "DEFAULT_5_DAY_BLUEPRINT",
    ),
    "InviteRejectedError": (
        "app.simulations.services.simulations_services_simulations_invite_errors_service",
        "InviteRejectedError",
    ),
    "SIMULATION_STATUS_ACTIVE_INVITING": (
        "app.simulations.repositories.simulations_repositories_simulations_simulation_status_constants",
        "SIMULATION_STATUS_ACTIVE_INVITING",
    ),
    "SIMULATION_STATUS_DRAFT": (
        "app.simulations.repositories.simulations_repositories_simulations_simulation_status_constants",
        "SIMULATION_STATUS_DRAFT",
    ),
    "SIMULATION_STATUS_GENERATING": (
        "app.simulations.repositories.simulations_repositories_simulations_simulation_status_constants",
        "SIMULATION_STATUS_GENERATING",
    ),
    "SIMULATION_STATUS_READY_FOR_REVIEW": (
        "app.simulations.repositories.simulations_repositories_simulations_simulation_status_constants",
        "SIMULATION_STATUS_READY_FOR_REVIEW",
    ),
    "SIMULATION_STATUS_TERMINATED": (
        "app.simulations.repositories.simulations_repositories_simulations_simulation_status_constants",
        "SIMULATION_STATUS_TERMINATED",
    ),
    "SIMULATION_CLEANUP_JOB_TYPE": (
        "app.simulations.services.simulations_services_simulations_cleanup_jobs_service",
        "SIMULATION_CLEANUP_JOB_TYPE",
    ),
    "_invite_is_expired": (
        "app.simulations.services.simulations_services_simulations_invite_tokens_service",
        "_invite_is_expired",
    ),
    "_refresh_invite_token": (
        "app.simulations.services.simulations_services_simulations_invite_tokens_service",
        "_refresh_invite_token",
    ),
    "_template_repo_for_task": (
        "app.simulations.services.simulations_services_simulations_task_templates_service",
        "_template_repo_for_task",
    ),
    "TerminateSimulationResult": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "TerminateSimulationResult",
    ),
    "activate_simulation": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "activate_simulation",
    ),
    "apply_status_transition": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "apply_status_transition",
    ),
    "build_simulation_cleanup_payload": (
        "app.simulations.services.simulations_services_simulations_cleanup_jobs_service",
        "build_simulation_cleanup_payload",
    ),
    "build_scenario_generation_payload": (
        "app.simulations.services.simulations_services_simulations_scenario_payload_builder_service",
        "build_scenario_generation_payload",
    ),
    "derive_candidate_compare_status": (
        "app.simulations.services.simulations_services_simulations_candidates_compare_service",
        "derive_candidate_compare_status",
    ),
    "derive_fit_profile_status": (
        "app.simulations.services.simulations_services_simulations_candidates_compare_service",
        "derive_fit_profile_status",
    ),
    "approve_scenario_version": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "approve_scenario_version",
    ),
    "create_initial_scenario_version": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "create_initial_scenario_version",
    ),
    "create_invite": (
        "app.simulations.services.simulations_services_simulations_invite_create_service",
        "create_invite",
    ),
    "create_or_resend_invite": (
        "app.simulations.services.simulations_services_simulations_invites_service",
        "create_or_resend_invite",
    ),
    "create_simulation_with_tasks": (
        "app.simulations.services.simulations_services_simulations_creation_service",
        "create_simulation_with_tasks",
    ),
    "cs_repo": ("app.candidates.candidate_sessions.repositories", "repository"),
    "ensure_scenario_version_mutable": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "ensure_scenario_version_mutable",
    ),
    "enqueue_simulation_cleanup_job": (
        "app.simulations.services.simulations_services_simulations_cleanup_jobs_service",
        "enqueue_simulation_cleanup_job",
    ),
    "get_active_scenario_version": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "get_active_scenario_version",
    ),
    "invite_url": (
        "app.simulations.services.simulations_services_simulations_urls_service",
        "invite_url",
    ),
    "lock_active_scenario_for_invites": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "lock_active_scenario_for_invites",
    ),
    "list_candidates_with_profile": (
        "app.simulations.services.simulations_services_simulations_listing_service",
        "list_candidates_with_profile",
    ),
    "list_candidates_compare_summary": (
        "app.simulations.services.simulations_services_simulations_candidates_compare_service",
        "list_candidates_compare_summary",
    ),
    "list_simulations": (
        "app.simulations.services.simulations_services_simulations_listing_service",
        "list_simulations",
    ),
    "normalize_simulation_status": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "normalize_simulation_status",
    ),
    "normalize_simulation_status_or_raise": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "normalize_simulation_status_or_raise",
    ),
    "patch_scenario_version": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "patch_scenario_version",
    ),
    "regenerate_active_scenario_version": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "regenerate_active_scenario_version",
    ),
    "request_scenario_regeneration": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "request_scenario_regeneration",
    ),
    "require_owner_for_lifecycle": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "require_owner_for_lifecycle",
    ),
    "require_owned_simulation": (
        "app.simulations.services.simulations_services_simulations_ownership_service",
        "require_owned_simulation",
    ),
    "require_owned_simulation_with_tasks": (
        "app.simulations.services.simulations_services_simulations_ownership_service",
        "require_owned_simulation_with_tasks",
    ),
    "require_simulation_compare_access": (
        "app.simulations.services.simulations_services_simulations_candidates_compare_service",
        "require_simulation_compare_access",
    ),
    "require_simulation_invitable": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "require_simulation_invitable",
    ),
    "resolve_template_repo_full_name": (
        "app.tasks.services.tasks_services_tasks_template_catalog_service",
        "resolve_template_repo_full_name",
    ),
    "scenario_repo": ("app.simulations.repositories.scenario_versions", "repository"),
    "settings": ("app.config", "settings"),
    "sim_repo": ("app.simulations.repositories", "repository"),
    "simulation_cleanup_idempotency_key": (
        "app.simulations.services.simulations_services_simulations_cleanup_jobs_service",
        "simulation_cleanup_idempotency_key",
    ),
    "terminate_simulation": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "terminate_simulation",
    ),
    "terminate_simulation_with_cleanup": (
        "app.simulations.services.simulations_services_simulations_lifecycle_service",
        "terminate_simulation_with_cleanup",
    ),
    "update_simulation": (
        "app.simulations.services.simulations_services_simulations_update_service",
        "update_simulation",
    ),
    "update_active_scenario_version": (
        "app.simulations.services.simulations_services_simulations_scenario_versions_service",
        "update_active_scenario_version",
    ),
}

__all__ = [
    *SIMULATIONS_EXPORTS,
    "candidates_compare",
    "creation",
    "invite_factory",
    "invite_preprovision",
    "invite_workflow",
    "lifecycle",
    "scenario_generation",
    "scenario_payload_builder",
    "scenario_versions",
    "task_templates",
    "update",
]


def __getattr__(name: str):
    target = _SYMBOL_ALIASES.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
