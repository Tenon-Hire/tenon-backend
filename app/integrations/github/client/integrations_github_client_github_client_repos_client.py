"""Application module for integrations github client github client repos client workflows."""

from __future__ import annotations

import logging

from .integrations_github_client_github_client_errors_client import GithubError
from .integrations_github_client_github_client_names_utils import split_full_name
from .integrations_github_client_github_client_transport_client import GithubTransport

logger = logging.getLogger(__name__)


def _normalize_generated_repo_identity(
    payload: dict, *, expected_owner: str, expected_repo_name: str
) -> tuple[str, str, str]:
    """Return the canonical owner/repo/full_name for a generated repository."""
    response_owner = ""
    response_repo = ""
    response_full_name = str(payload.get("full_name") or "").strip()

    if response_full_name:
        try:
            full_name_owner, full_name_repo = split_full_name(response_full_name)
        except GithubError:
            response_full_name = ""
        else:
            response_owner = full_name_owner
            response_repo = full_name_repo

    owner_value = payload.get("owner")
    if isinstance(owner_value, dict):
        owner_value = owner_value.get("login") or owner_value.get("name")
    owner_value = str(owner_value or "").strip()
    repo_value = str(payload.get("name") or "").strip()

    if owner_value and response_owner and owner_value != response_owner:
        raise GithubError(
            "GitHub repository creation returned an inconsistent repository owner"
        )
    if repo_value and response_repo and repo_value != response_repo:
        raise GithubError(
            "GitHub repository creation returned an inconsistent repository name"
        )
    if owner_value:
        response_owner = owner_value
    if repo_value:
        response_repo = repo_value

    if not response_owner or not response_repo:
        raise GithubError("GitHub repository creation returned an invalid payload")

    canonical_full_name = f"{response_owner}/{response_repo}"
    if response_full_name and response_full_name != canonical_full_name:
        raise GithubError(
            "GitHub repository creation returned an inconsistent repository identity"
        )

    if response_owner != expected_owner:
        logger.error(
            "github_repo_created_under_unexpected_owner",
            extra={
                "expected_owner": expected_owner,
                "returned_owner": response_owner,
                "repo_name": response_repo,
            },
        )
        raise GithubError("GitHub repository was created under an unexpected owner")
    if response_repo != expected_repo_name:
        logger.error(
            "github_repo_created_with_unexpected_name",
            extra={
                "expected_repo_name": expected_repo_name,
                "returned_repo_name": response_repo,
                "owner": response_owner,
            },
        )
        raise GithubError("GitHub repository was created with an unexpected name")

    return response_owner, response_repo, canonical_full_name


class RepoOperations:
    """Represent repo operations data and behavior."""

    transport: GithubTransport
    default_org: str | None

    async def generate_repo_from_template(
        self,
        *,
        template_full_name: str,
        new_repo_name: str,
        owner: str | None = None,
        private: bool = True,
    ) -> dict:
        """Generate repo from template."""
        template_owner, template_repo = split_full_name(template_full_name)
        resolved_owner = (owner or self.default_org or "").strip()
        if not resolved_owner:
            raise GithubError("Destination GitHub org is not configured")
        payload = {
            "owner": resolved_owner,
            "name": new_repo_name,
            "include_all_branches": False,
            "private": private,
        }
        path = f"/repos/{template_owner}/{template_repo}/generate"
        generated = await self._request("POST", path, json=payload)
        (
            response_owner,
            response_repo,
            response_full_name,
        ) = _normalize_generated_repo_identity(
            generated,
            expected_owner=resolved_owner,
            expected_repo_name=new_repo_name,
        )
        generated["name"] = response_repo
        generated["full_name"] = response_full_name
        generated["canonical_owner"] = response_owner
        generated["canonical_name"] = response_repo
        generated["canonical_full_name"] = response_full_name
        return generated

    async def add_collaborator(
        self, repo_full_name: str, username: str, *, permission: str = "push"
    ) -> dict:
        """Add collaborator."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/collaborators/{username}"
        return await self._request("PUT", path, json={"permission": permission})

    async def remove_collaborator(self, repo_full_name: str, username: str) -> dict:
        """Remove collaborator."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/collaborators/{username}"
        return await self._request("DELETE", path, expect_body=False)

    async def archive_repo(self, repo_full_name: str) -> dict:
        """Execute archive repo."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}"
        return await self._request("PATCH", path, json={"archived": True})

    async def delete_repo(self, repo_full_name: str) -> dict:
        """Delete repo."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}"
        return await self._request("DELETE", path, expect_body=False)
