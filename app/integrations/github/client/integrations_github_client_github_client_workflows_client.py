"""Application module for integrations github client github client workflows client workflows."""

from __future__ import annotations

from .integrations_github_client_github_client_names_utils import split_full_name
from .integrations_github_client_github_client_runs_model import WorkflowRun, parse_run
from .integrations_github_client_github_client_transport_client import GithubTransport


class WorkflowOperations:
    """Represent workflow operations data and behavior."""

    transport: GithubTransport

    async def trigger_workflow_dispatch(
        self,
        repo_full_name: str,
        workflow_id_or_file: str,
        *,
        ref: str,
        inputs: dict | None = None,
    ) -> None:
        """Execute trigger workflow dispatch."""
        owner, repo = split_full_name(repo_full_name)
        path = (
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_file}/dispatches"
        )
        await self._request(
            "POST",
            path,
            json={"ref": ref, "inputs": inputs or {}},
            expect_body=False,
        )

    async def get_workflow_run(self, repo_full_name: str, run_id: int) -> WorkflowRun:
        """Return workflow run."""
        owner, repo = split_full_name(repo_full_name)
        path = f"/repos/{owner}/{repo}/actions/runs/{run_id}"
        data = await self._get_json(path)
        return parse_run(data)

    async def list_workflow_runs(
        self,
        repo_full_name: str,
        workflow_id_or_file: str,
        *,
        branch: str | None = None,
        per_page: int = 5,
    ) -> list[WorkflowRun]:
        """Return workflow runs."""
        owner, repo = split_full_name(repo_full_name)
        params = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        path = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_file}/runs"
        data = await self._get_json(path, params=params)
        runs = data.get("workflow_runs") or []
        return [parse_run(r) for r in runs]
