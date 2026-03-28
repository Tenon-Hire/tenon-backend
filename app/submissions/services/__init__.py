"""Application module for init workflows."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)
from app.submissions.services.submissions_services_submissions_branch_validation_service import (
    validate_branch,
)
from app.submissions.services.submissions_services_submissions_create_submission_service import (
    create_submission,
)
from app.submissions.services.submissions_services_submissions_diff_summary_service import (
    summarize_diff,
)
from app.submissions.services.submissions_services_submissions_github_user_service import (
    validate_github_username,
)
from app.submissions.services.submissions_services_submissions_payload_validation_service import (
    CODE_TASK_TYPES,
    TEXT_TASK_TYPES,
    is_code_task,
    validate_run_allowed,
    validate_submission_payload,
)
from app.submissions.services.submissions_services_submissions_repo_naming_service import (
    build_repo_name,
    validate_repo_full_name,
)
from app.submissions.services.submissions_services_submissions_run_service import (
    run_actions_tests,
)
from app.submissions.services.submissions_services_submissions_submission_progress_service import (
    progress_after_submission,
)
from app.submissions.services.submissions_services_submissions_task_lookup_service import (
    load_task_or_404,
)
from app.submissions.services.submissions_services_submissions_task_rules_service import (
    ensure_in_order,
    ensure_not_duplicate,
    ensure_task_belongs,
)
from app.submissions.services.submissions_services_submissions_workspace_provision_service import (
    ensure_workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_records_service import (
    build_codespace_url,
    record_run_result,
)

_MODULE_ALIASES = {
    "branch_validation": "app.submissions.services.submissions_services_submissions_branch_validation_service",
    "codespace_urls": "app.submissions.services.submissions_services_submissions_codespace_urls_service",
    "create_submission": "app.submissions.services.submissions_services_submissions_create_submission_service",
    "diff_summary": "app.submissions.services.submissions_services_submissions_diff_summary_service",
    "github_user": "app.submissions.services.submissions_services_submissions_github_user_service",
    "payload_validation": "app.submissions.services.submissions_services_submissions_payload_validation_service",
    "rate_limits": "app.submissions.services.submissions_services_submissions_rate_limits_constants",
    "repo_naming": "app.submissions.services.submissions_services_submissions_repo_naming_service",
    "run_service": "app.submissions.services.submissions_services_submissions_run_service",
    "candidate_service": "app.submissions.services.submissions_services_submissions_candidate_service",
    "service_candidate": "app.submissions.services.submissions_services_submissions_candidate_service",
    "submission_actions": "app.submissions.services.submissions_services_submissions_submission_actions_service",
    "submission_builder": "app.submissions.services.submissions_services_submissions_submission_builder_service",
    "submission_progress": "app.submissions.services.submissions_services_submissions_submission_progress_service",
    "task_lookup": "app.submissions.services.submissions_services_submissions_task_lookup_service",
    "task_rules": "app.submissions.services.submissions_services_submissions_task_rules_service",
    "workspace_cleanup_jobs": "app.submissions.services.submissions_services_submissions_workspace_cleanup_jobs_service",
    "workspace_creation": "app.submissions.services.submissions_services_submissions_workspace_creation_service",
    "workspace_creation_group_repo": "app.submissions.services.submissions_services_submissions_workspace_creation_group_repo_service",
    "workspace_creation_group_repo_create": "app.submissions.services.submissions_services_submissions_workspace_creation_group_repo_create_service",
    "workspace_creation_grouped": "app.submissions.services.submissions_services_submissions_workspace_creation_grouped_service",
    "workspace_creation_grouped_hydration": "app.submissions.services.submissions_services_submissions_workspace_creation_grouped_hydration_service",
    "workspace_creation_precommit": "app.submissions.services.submissions_services_submissions_workspace_creation_precommit_service",
    "workspace_creation_provision": "app.submissions.services.submissions_services_submissions_workspace_creation_provision_service",
    "workspace_creation_single": "app.submissions.services.submissions_services_submissions_workspace_creation_single_service",
    "workspace_creation_strategy": "app.submissions.services.submissions_services_submissions_workspace_creation_strategy_service",
    "workspace_existing": "app.submissions.services.submissions_services_submissions_workspace_existing_service",
    "workspace_precommit_bundle": "app.submissions.services.submissions_services_submissions_workspace_precommit_bundle_service",
    "workspace_provision": "app.submissions.services.submissions_services_submissions_workspace_provision_service",
    "workspace_records": "app.submissions.services.submissions_services_submissions_workspace_records_service",
    "workspace_repo_state": "app.submissions.services.submissions_services_submissions_workspace_repo_state_service",
    "workspace_template_repo": "app.submissions.services.submissions_services_submissions_workspace_template_repo_service",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = [
    "CODE_TASK_TYPES",
    "TEXT_TASK_TYPES",
    "build_codespace_url",
    "build_repo_name",
    "create_submission",
    "ensure_in_order",
    "ensure_not_duplicate",
    "ensure_task_belongs",
    "ensure_workspace",
    "is_code_task",
    "load_task_or_404",
    "progress_after_submission",
    "record_run_result",
    "run_actions_tests",
    "summarize_diff",
    "validate_branch",
    "validate_github_username",
    "validate_repo_full_name",
    "validate_run_allowed",
    "validate_submission_payload",
    *_MODULE_ALIASES.keys(),
]


def __getattr__(name: str):  # pragma: no cover
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
