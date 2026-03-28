"""Application module for submissions services submissions workspace creation single service workflows."""

from __future__ import annotations

from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_precommit_service import (
    persist_precommit_result,
)
from app.submissions.services.submissions_services_submissions_workspace_precommit_bundle_service import (
    apply_precommit_bundle_if_available,
)
from app.submissions.services.submissions_services_submissions_workspace_records_service import (
    build_codespace_url,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    add_collaborator_if_needed,
    fetch_base_template_sha,
)
from app.submissions.services.submissions_services_submissions_workspace_template_repo_service import (
    generate_template_repo,
)


async def provision_single_workspace(
    db,
    candidate_session,
    task,
    github_client,
    github_username,
    repo_prefix,
    template_default_owner,
    now,
    commit,
    hydrate_precommit_bundle,
):
    """Execute provision single workspace."""
    (
        template_repo,
        repo_full_name,
        default_branch,
        repo_id,
    ) = await generate_template_repo(
        github_client=github_client,
        candidate_session=candidate_session,
        task=task,
        repo_prefix=repo_prefix,
        template_default_owner=template_default_owner,
        workspace_key=None,
    )
    base_template_sha = await fetch_base_template_sha(
        github_client, repo_full_name, default_branch
    )
    await add_collaborator_if_needed(github_client, repo_full_name, github_username)
    create_workspace_kwargs = {
        "candidate_session_id": candidate_session.id,
        "task_id": task.id,
        "template_repo_full_name": template_repo,
        "repo_full_name": repo_full_name,
        "repo_id": repo_id,
        "default_branch": default_branch,
        "base_template_sha": base_template_sha,
        "codespace_url": build_codespace_url(repo_full_name),
        "created_at": now,
    }
    if not commit:
        create_workspace_kwargs["commit"] = False
        create_workspace_kwargs["refresh"] = False
    workspace = await workspace_repo.create_workspace(db, **create_workspace_kwargs)
    if not hydrate_precommit_bundle:
        return workspace
    precommit_result = await apply_precommit_bundle_if_available(
        db,
        github_client=github_client,
        candidate_session=candidate_session,
        task=task,
        repo_full_name=workspace.repo_full_name,
        default_branch=workspace.default_branch,
        base_template_sha=workspace.base_template_sha,
        existing_precommit_sha=workspace.precommit_sha,
    )
    return await persist_precommit_result(
        db, workspace=workspace, precommit_result=precommit_result, commit=commit
    )
