"""Application module for init workflows."""

from __future__ import annotations

from importlib import import_module

from . import (
    trials_services_trials_candidates_compare_service as candidates_compare,
)
from . import trials_services_trials_creation_service as creation
from . import trials_services_trials_invite_factory_service as invite_factory
from . import (
    trials_services_trials_invite_preprovision_service as invite_preprovision,
)
from . import (
    trials_services_trials_invite_workflow_service as invite_workflow,
)
from . import trials_services_trials_lifecycle_service as lifecycle
from . import (
    trials_services_trials_scenario_generation_service as scenario_generation,
)
from . import (
    trials_services_trials_scenario_payload_builder_service as scenario_payload_builder,
)
from . import (
    trials_services_trials_scenario_versions_service as scenario_versions,
)
from . import trials_services_trials_task_templates_service as task_templates
from . import trials_services_trials_update_service as update
from .trials_services_trials_exports_service import TRIALS_EXPORTS

_SYMBOL_ALIASES: dict[str, tuple[str, str]] = {
    "ApiError": ("app.shared.utils.shared_utils_errors_utils", "ApiError"),
    "DEFAULT_5_DAY_BLUEPRINT": (
        "app.trials.constants.trials_constants_trials_blueprints_constants",
        "DEFAULT_5_DAY_BLUEPRINT",
    ),
    "InviteRejectedError": (
        "app.trials.services.trials_services_trials_invite_errors_service",
        "InviteRejectedError",
    ),
    "TRIAL_STATUS_ACTIVE_INVITING": (
        "app.trials.repositories.trials_repositories_trials_trial_status_constants",
        "TRIAL_STATUS_ACTIVE_INVITING",
    ),
    "TRIAL_STATUS_DRAFT": (
        "app.trials.repositories.trials_repositories_trials_trial_status_constants",
        "TRIAL_STATUS_DRAFT",
    ),
    "TRIAL_STATUS_GENERATING": (
        "app.trials.repositories.trials_repositories_trials_trial_status_constants",
        "TRIAL_STATUS_GENERATING",
    ),
    "TRIAL_STATUS_READY_FOR_REVIEW": (
        "app.trials.repositories.trials_repositories_trials_trial_status_constants",
        "TRIAL_STATUS_READY_FOR_REVIEW",
    ),
    "TRIAL_STATUS_TERMINATED": (
        "app.trials.repositories.trials_repositories_trials_trial_status_constants",
        "TRIAL_STATUS_TERMINATED",
    ),
    "TRIAL_CLEANUP_JOB_TYPE": (
        "app.trials.services.trials_services_trials_cleanup_jobs_service",
        "TRIAL_CLEANUP_JOB_TYPE",
    ),
    "_invite_is_expired": (
        "app.trials.services.trials_services_trials_invite_tokens_service",
        "_invite_is_expired",
    ),
    "_refresh_invite_token": (
        "app.trials.services.trials_services_trials_invite_tokens_service",
        "_refresh_invite_token",
    ),
    "_template_repo_for_task": (
        "app.trials.services.trials_services_trials_task_templates_service",
        "_template_repo_for_task",
    ),
    "TerminateTrialResult": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "TerminateTrialResult",
    ),
    "activate_trial": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "activate_trial",
    ),
    "apply_status_transition": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "apply_status_transition",
    ),
    "build_trial_cleanup_payload": (
        "app.trials.services.trials_services_trials_cleanup_jobs_service",
        "build_trial_cleanup_payload",
    ),
    "build_scenario_generation_payload": (
        "app.trials.services.trials_services_trials_scenario_payload_builder_service",
        "build_scenario_generation_payload",
    ),
    "derive_candidate_compare_status": (
        "app.trials.services.trials_services_trials_candidates_compare_service",
        "derive_candidate_compare_status",
    ),
    "derive_winoe_report_status": (
        "app.trials.services.trials_services_trials_candidates_compare_service",
        "derive_winoe_report_status",
    ),
    "approve_scenario_version": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "approve_scenario_version",
    ),
    "create_initial_scenario_version": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "create_initial_scenario_version",
    ),
    "create_invite": (
        "app.trials.services.trials_services_trials_invite_create_service",
        "create_invite",
    ),
    "create_or_resend_invite": (
        "app.trials.services.trials_services_trials_invites_service",
        "create_or_resend_invite",
    ),
    "create_trial_with_tasks": (
        "app.trials.services.trials_services_trials_creation_service",
        "create_trial_with_tasks",
    ),
    "cs_repo": ("app.candidates.candidate_sessions.repositories", "repository"),
    "ensure_scenario_version_mutable": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "ensure_scenario_version_mutable",
    ),
    "enqueue_trial_cleanup_job": (
        "app.trials.services.trials_services_trials_cleanup_jobs_service",
        "enqueue_trial_cleanup_job",
    ),
    "get_active_scenario_version": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "get_active_scenario_version",
    ),
    "invite_url": (
        "app.trials.services.trials_services_trials_urls_service",
        "invite_url",
    ),
    "lock_active_scenario_for_invites": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "lock_active_scenario_for_invites",
    ),
    "list_candidates_with_profile": (
        "app.trials.services.trials_services_trials_listing_service",
        "list_candidates_with_profile",
    ),
    "list_candidates_compare_summary": (
        "app.trials.services.trials_services_trials_candidates_compare_service",
        "list_candidates_compare_summary",
    ),
    "list_trials": (
        "app.trials.services.trials_services_trials_listing_service",
        "list_trials",
    ),
    "normalize_trial_status": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "normalize_trial_status",
    ),
    "normalize_trial_status_or_raise": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "normalize_trial_status_or_raise",
    ),
    "patch_scenario_version": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "patch_scenario_version",
    ),
    "regenerate_active_scenario_version": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "regenerate_active_scenario_version",
    ),
    "request_scenario_regeneration": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "request_scenario_regeneration",
    ),
    "require_owner_for_lifecycle": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "require_owner_for_lifecycle",
    ),
    "require_owned_trial": (
        "app.trials.services.trials_services_trials_ownership_service",
        "require_owned_trial",
    ),
    "require_owned_trial_with_tasks": (
        "app.trials.services.trials_services_trials_ownership_service",
        "require_owned_trial_with_tasks",
    ),
    "require_trial_compare_access": (
        "app.trials.services.trials_services_trials_candidates_compare_service",
        "require_trial_compare_access",
    ),
    "require_trial_invitable": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "require_trial_invitable",
    ),
    "resolve_template_repo_full_name": (
        "app.tasks.services.tasks_services_tasks_template_catalog_service",
        "resolve_template_repo_full_name",
    ),
    "scenario_repo": ("app.trials.repositories.scenario_versions", "repository"),
    "settings": ("app.config", "settings"),
    "sim_repo": ("app.trials.repositories", "repository"),
    "trial_cleanup_idempotency_key": (
        "app.trials.services.trials_services_trials_cleanup_jobs_service",
        "trial_cleanup_idempotency_key",
    ),
    "terminate_trial": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "terminate_trial",
    ),
    "terminate_trial_with_cleanup": (
        "app.trials.services.trials_services_trials_lifecycle_service",
        "terminate_trial_with_cleanup",
    ),
    "update_trial": (
        "app.trials.services.trials_services_trials_update_service",
        "update_trial",
    ),
    "update_active_scenario_version": (
        "app.trials.services.trials_services_trials_scenario_versions_service",
        "update_active_scenario_version",
    ),
}

__all__ = [
    *TRIALS_EXPORTS,
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
