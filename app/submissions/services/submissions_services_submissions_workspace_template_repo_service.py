"""Application module for submissions services submissions workspace template repo service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.services.submissions_services_submissions_repo_naming_service import (
    build_repo_name,
    validate_repo_full_name,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    normalize_template_repo_value,
)


async def generate_template_repo(
    *,
    github_client: GithubClient,
    candidate_session: CandidateSession,
    task: Task,
    repo_prefix: str,
    destination_owner: str | None,
    workspace_key: str | None = None,
) -> tuple[str, str, str | None, int | None]:
    """Generate template repo."""
    template_repo = normalize_template_repo_value(task.template_repo)
    if not template_repo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task template repository is not configured",
        )
    validate_repo_full_name(template_repo)
    resolved_owner = (destination_owner or "").strip()
    if not resolved_owner:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub destination org is not configured",
        )

    new_repo_name = build_repo_name(
        prefix=repo_prefix,
        candidate_session=candidate_session,
        task=task,
        workspace_key=workspace_key,
    )
    generated = await github_client.generate_repo_from_template(
        template_full_name=template_repo,
        new_repo_name=new_repo_name,
        owner=resolved_owner,
        private=True,
    )

    owner_value = generated.get("canonical_owner")
    if not owner_value:
        owner_value = generated.get("owner")
        if isinstance(owner_value, dict):
            owner_value = owner_value.get("login") or owner_value.get("name")
    repo_name = str(
        generated.get("canonical_name") or generated.get("name") or ""
    ).strip()
    repo_full_name = str(
        generated.get("canonical_full_name") or generated.get("full_name") or ""
    ).strip()
    if repo_full_name:
        try:
            full_name_owner, full_name_repo = repo_full_name.split("/", 1)
        except ValueError:
            full_name_owner = ""
            full_name_repo = ""
        else:
            full_name_owner = full_name_owner.strip()
            full_name_repo = full_name_repo.strip()
            if not owner_value:
                owner_value = full_name_owner
            if not repo_name:
                repo_name = full_name_repo
            if owner_value and full_name_owner and owner_value != full_name_owner:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="GitHub repo generation returned an inconsistent repository identity",
                )
            if repo_name and full_name_repo and repo_name != full_name_repo:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="GitHub repo generation returned an inconsistent repository identity",
                )
    expected_full_name = f"{resolved_owner}/{new_repo_name}"
    default_branch = generated.get("default_branch") or generated.get("master_branch")
    repo_id = generated.get("id")
    if owner_value and repo_name and not repo_full_name:
        repo_full_name = f"{owner_value}/{repo_name}"
    if not owner_value or not repo_name or not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repo generation returned an invalid repository identity",
        )
    generated_owner = str(owner_value or "").strip()
    if generated_owner != resolved_owner:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repo generation returned an unexpected destination owner",
        )
    if repo_name != new_repo_name:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repo generation returned an unexpected repository name",
        )
    if repo_full_name != expected_full_name:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repo generation returned an inconsistent repository identity",
        )
    validate_repo_full_name(repo_full_name)
    return template_repo, repo_full_name, default_branch, repo_id
