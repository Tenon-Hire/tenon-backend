"""Application module for submissions services submissions workspace template repo service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.services.submissions_services_submissions_repo_naming_service import (
    build_repo_name,
    validate_repo_full_name,
)


async def generate_template_repo(
    *,
    github_client: GithubClient,
    candidate_session: CandidateSession,
    task: Task,
    repo_prefix: str,
    template_default_owner: str | None,
    workspace_key: str | None = None,
) -> tuple[str, str, str | None, int | None]:
    """Generate template repo."""
    template_repo = (task.template_repo or "").strip()
    if not template_repo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task template repository is not configured",
        )
    validate_repo_full_name(template_repo)

    new_repo_name = build_repo_name(
        prefix=repo_prefix,
        candidate_session=candidate_session,
        task=task,
        workspace_key=workspace_key,
    )
    template_owner = template_repo.split("/")[0] if "/" in template_repo else None
    generated = await github_client.generate_repo_from_template(
        template_full_name=template_repo,
        new_repo_name=new_repo_name,
        owner=template_owner or template_default_owner,
        private=True,
    )

    repo_full_name = generated.get("full_name") or ""
    default_branch = generated.get("default_branch") or generated.get("master_branch")
    repo_id = generated.get("id")
    validate_repo_full_name(repo_full_name)
    return template_repo, repo_full_name, default_branch, repo_id
