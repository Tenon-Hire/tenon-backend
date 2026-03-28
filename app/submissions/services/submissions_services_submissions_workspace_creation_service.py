"""Application module for submissions services submissions workspace creation service workflows."""

from __future__ import annotations

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_group_repo_create_service as _group_repo_create_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_group_repo_service as _group_repo_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_grouped_hydration_service as _grouped_hydration_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_grouped_service as _grouped_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_precommit_service as _precommit_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_provision_service as _provision_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_single_service as _single_module,
)
from app.submissions.services.submissions_services_submissions_workspace_precommit_bundle_service import (
    apply_precommit_bundle_if_available,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    add_collaborator_if_needed,
    fetch_base_template_sha,
)
from app.submissions.services.submissions_services_submissions_workspace_template_repo_service import (
    generate_template_repo,
)


def _sync_dependencies() -> None:
    _single_module.generate_template_repo = generate_template_repo
    _single_module.fetch_base_template_sha = fetch_base_template_sha
    _single_module.add_collaborator_if_needed = add_collaborator_if_needed
    _single_module.apply_precommit_bundle_if_available = (
        apply_precommit_bundle_if_available
    )
    _grouped_hydration_module.add_collaborator_if_needed = add_collaborator_if_needed
    _grouped_hydration_module.apply_precommit_bundle_if_available = (
        apply_precommit_bundle_if_available
    )
    _group_repo_create_module.generate_template_repo = generate_template_repo
    _group_repo_create_module.add_collaborator_if_needed = add_collaborator_if_needed
    _group_repo_module.fetch_base_template_sha = fetch_base_template_sha
    _group_repo_module.add_collaborator_if_needed = add_collaborator_if_needed


def _serialize_no_bundle_details(precommit_result: object) -> str | None:
    return _precommit_module.serialize_no_bundle_details(precommit_result)


async def _get_or_create_workspace_group(*args, **kwargs):
    _sync_dependencies()
    return await _group_repo_module.get_or_create_workspace_group(*args, **kwargs)


async def _provision_grouped_workspace(*args, **kwargs):
    _sync_dependencies()
    _grouped_module.get_or_create_workspace_group = _get_or_create_workspace_group
    return await _grouped_module.provision_grouped_workspace(*args, **kwargs)


async def provision_workspace(*args, **kwargs):
    """Execute provision workspace."""
    _sync_dependencies()
    _provision_module.provision_grouped_workspace = _provision_grouped_workspace
    _provision_module.provision_single_workspace = (
        _single_module.provision_single_workspace
    )
    return await _provision_module.provision_workspace(*args, **kwargs)


__all__ = [
    "provision_workspace",
    "_get_or_create_workspace_group",
    "_provision_grouped_workspace",
    "_serialize_no_bundle_details",
    "workspace_repo",
    "generate_template_repo",
    "fetch_base_template_sha",
    "add_collaborator_if_needed",
    "apply_precommit_bundle_if_available",
]
