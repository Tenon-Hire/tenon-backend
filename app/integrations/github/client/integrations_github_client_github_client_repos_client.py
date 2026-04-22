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

    async def create_empty_repo(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool = True,
        default_branch: str = "main",
    ) -> dict:
        """Create an empty repository under an organization."""
        resolved_owner = (owner or "").strip()
        resolved_repo_name = (repo_name or "").strip()
        if not resolved_owner:
            raise GithubError("Destination GitHub org is not configured")
        if not resolved_repo_name:
            raise GithubError("Repository name is not configured")
        payload = {
            "name": resolved_repo_name,
            "private": private,
            "auto_init": False,
            "default_branch": default_branch,
        }
        path = f"/orgs/{resolved_owner}/repos"
        generated = await self._post_json(path, json=payload)
        (
            response_owner,
            response_repo,
            response_full_name,
        ) = _normalize_generated_repo_identity(
            generated,
            expected_owner=resolved_owner,
            expected_repo_name=resolved_repo_name,
        )
        generated["name"] = response_repo
        generated["full_name"] = response_full_name
        generated["canonical_owner"] = response_owner
        generated["canonical_name"] = response_repo
        generated["canonical_full_name"] = response_full_name
        return generated

    async def create_codespace(
        self,
        repo_full_name: str,
        *,
        ref: str | None = None,
        devcontainer_path: str = ".devcontainer/devcontainer.json",
        machine: str | None = None,
        location: str | None = None,
    ) -> dict:
        """Create a GitHub Codespace for a repository."""
        owner, repo = split_full_name(repo_full_name)
        payload: dict[str, str] = {}
        if ref:
            payload["ref"] = ref
        if devcontainer_path:
            payload["devcontainer_path"] = devcontainer_path
        if machine:
            payload["machine"] = machine
        if location:
            payload["location"] = location
        return await self._post_json(
            f"/repos/{owner}/{repo}/codespaces",
            json=payload,
        )

    async def get_authenticated_user_login(self) -> str | None:
        """Return the login for the token's authenticated GitHub user."""
        payload = await self._get_json("/user")
        if not isinstance(payload, dict):
            return None
        login = str(payload.get("login") or payload.get("username") or "").strip()
        return login or None

    async def get_codespace(self, repo_full_name: str, codespace_name: str) -> dict:
        """Return a GitHub Codespace by name."""
        expected_owner, expected_repo = split_full_name(repo_full_name)
        payload = await self._get_json(f"/user/codespaces/{codespace_name}")

        repository = payload.get("repository")
        if isinstance(repository, dict):
            returned_full_name = str(repository.get("full_name") or "").strip()
            if returned_full_name:
                returned_owner, returned_repo = split_full_name(returned_full_name)
                if returned_owner != expected_owner or returned_repo != expected_repo:
                    raise GithubError(
                        "GitHub Codespace lookup returned an unexpected repository"
                    )
        return payload

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

    async def create_ref(self, repo_full_name: str, *, ref: str, sha: str) -> dict:
        """Create a git ref."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/git/refs"
        return await self._post_json(path, json={"ref": ref, "sha": sha})

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
