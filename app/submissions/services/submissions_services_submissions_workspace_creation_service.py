"""Application module for submissions services submissions workspace creation service workflows."""

from __future__ import annotations

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
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
    submissions_services_submissions_workspace_creation_provision_service as _provision_module,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_single_service as _single_module,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_group_repo_create_service import (
    create_group_repo,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_group_repo_service import (
    get_or_create_workspace_group,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_grouped_hydration_service import (
    hydrate_existing_workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_grouped_service import (
    provision_grouped_workspace as _grouped_provision_workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_precommit_service import (
    serialize_no_bundle_details as _serialize_no_bundle_details_impl,
)
from app.submissions.services.submissions_services_submissions_workspace_precommit_bundle_service import (
    apply_precommit_bundle_if_available,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    add_collaborator_if_needed,
)


def _sync_dependencies() -> None:
    _single_module.add_collaborator_if_needed = add_collaborator_if_needed
    _single_module.apply_precommit_bundle_if_available = (
        apply_precommit_bundle_if_available
    )
    _grouped_hydration_module.add_collaborator_if_needed = add_collaborator_if_needed
    _grouped_hydration_module.apply_precommit_bundle_if_available = (
        apply_precommit_bundle_if_available
    )
    _group_repo_module.add_collaborator_if_needed = add_collaborator_if_needed


async def provision_workspace(*args, **kwargs):
    """Execute provision workspace."""
    _sync_dependencies()
    _grouped_module.get_or_create_workspace_group = _get_or_create_workspace_group
    _provision_module.provision_grouped_workspace = _provision_grouped_workspace
    _provision_module.provision_single_workspace = (
        _single_module.provision_single_workspace
    )
    return await _provision_module.provision_workspace(*args, **kwargs)


async def _get_or_create_workspace_group(*args, **kwargs):
    _sync_dependencies()
    result = await _group_repo_module.get_or_create_workspace_group(*args, **kwargs)
    if isinstance(result, tuple) and len(result) == 2:
        group, repo_id = result
        return group, repo_id, None, None, None
    return result


async def _provision_grouped_workspace(*args, **kwargs):
    _sync_dependencies()
    _grouped_module.get_or_create_workspace_group = _get_or_create_workspace_group
    _grouped_hydration_module.get_or_create_workspace_group = (
        _get_or_create_workspace_group
    )
    return await _grouped_module.provision_grouped_workspace(*args, **kwargs)


def _serialize_no_bundle_details(precommit_result: object) -> str | None:
    return _serialize_no_bundle_details_impl(precommit_result)


__all__ = [
    "provision_workspace",
    "_get_or_create_workspace_group",
    "_provision_grouped_workspace",
    "_serialize_no_bundle_details",
    "workspace_repo",
    "create_group_repo",
    "get_or_create_workspace_group",
    "hydrate_existing_workspace",
    "_grouped_provision_workspace",
    "_serialize_no_bundle_details_impl",
    "add_collaborator_if_needed",
    "apply_precommit_bundle_if_available",
]
