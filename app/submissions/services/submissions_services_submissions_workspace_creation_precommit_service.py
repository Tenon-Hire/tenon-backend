"""Application module for submissions services submissions workspace creation precommit service workflows."""

from __future__ import annotations

import json

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)


def serialize_no_bundle_details(precommit_result: object) -> str | None:
    """Serialize no bundle details."""
    if getattr(precommit_result, "state", None) != "no_bundle":
        return None
    details = getattr(precommit_result, "details", None)
    if not isinstance(details, dict):
        return None
    payload = {"state": "no_bundle", **details}
    return json.dumps(payload, sort_keys=True)


async def persist_precommit_result(
    db, *, workspace: Workspace, precommit_result, commit: bool
) -> Workspace:
    """Execute persist precommit result."""
    if (
        precommit_result.precommit_sha
        and workspace.precommit_sha != precommit_result.precommit_sha
    ):
        if commit:
            return await workspace_repo.set_precommit_sha(
                db,
                workspace=workspace,
                precommit_sha=precommit_result.precommit_sha,
            )
        return await workspace_repo.set_precommit_sha(
            db,
            workspace=workspace,
            precommit_sha=precommit_result.precommit_sha,
            commit=False,
            refresh=False,
        )
    no_bundle_details_json = serialize_no_bundle_details(precommit_result)
    if (
        no_bundle_details_json
        and workspace.precommit_details_json != no_bundle_details_json
    ):
        if commit:
            return await workspace_repo.set_precommit_details(
                db,
                workspace=workspace,
                precommit_details_json=no_bundle_details_json,
            )
        return await workspace_repo.set_precommit_details(
            db,
            workspace=workspace,
            precommit_details_json=no_bundle_details_json,
            commit=False,
            refresh=False,
        )
    return workspace
