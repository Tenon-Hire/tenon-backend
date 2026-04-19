"""Application module for submissions services submissions workspace creation provision service workflows."""

from __future__ import annotations

from datetime import datetime

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Task,
    Trial,
)
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    WorkspaceMissing,
)
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_keys_repository as wk,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_grouped_service import (
    provision_grouped_workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_single_service import (
    provision_single_workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_strategy_service import (
    resolve_workspace_strategy,
)
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)


async def _resolve_bootstrap_context(db, *, task: Task, trial, scenario_version):
    """Load bootstrap context when callers only provide the task."""
    resolved_trial = trial
    if resolved_trial is None and getattr(task, "trial_id", None) is not None:
        resolved_trial = await db.get(Trial, task.trial_id)
    resolved_scenario_version = scenario_version
    if resolved_scenario_version is None and resolved_trial is not None:
        resolved_scenario_version = await scenario_repo.get_active_for_trial(
            db, resolved_trial.id
        )
    return resolved_trial, resolved_scenario_version


async def provision_workspace(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    github_client: GithubClient,
    github_username: str | None,
    repo_prefix: str,
    destination_owner: str | None,
    now: datetime,
    workspace_resolution: workspace_repo.WorkspaceResolution | None = None,
    commit: bool = True,
    hydrate_precommit_bundle: bool = True,
    bootstrap_empty_repo: bool = False,
    trial=None,
    scenario_version=None,
) -> Workspace:
    """Execute provision workspace."""
    trial, scenario_version = await _resolve_bootstrap_context(
        db,
        task=task,
        trial=trial,
        scenario_version=scenario_version,
    )
    (
        workspace_key,
        uses_grouped_workspace,
        existing_group,
        checked,
    ) = await resolve_workspace_strategy(
        db, candidate_session, task, workspace_resolution
    )
    if (
        uses_grouped_workspace
        and workspace_key == wk.CODING_WORKSPACE_KEY
        and getattr(task, "day_index", None) == 3
        and existing_group is None
    ):
        raise WorkspaceMissing(
            detail=(
                "Workspace not initialized. "
                "Call Day 2 /codespace/init first on the shared coding workspace."
            )
        )
    if uses_grouped_workspace:
        return await provision_grouped_workspace(
            db,
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=task,
            workspace_key=workspace_key,
            github_client=github_client,
            github_username=github_username,
            repo_prefix=repo_prefix,
            destination_owner=destination_owner,
            now=now,
            existing_group=existing_group,
            commit=commit,
            hydrate_precommit_bundle=hydrate_precommit_bundle,
            existing_checked=True,
            workspace_group_checked=checked,
            bootstrap_empty_repo=bootstrap_empty_repo,
        )
    return await provision_single_workspace(
        db,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=task,
        github_client=github_client,
        github_username=github_username,
        repo_prefix=repo_prefix,
        destination_owner=destination_owner,
        now=now,
        commit=commit,
        hydrate_precommit_bundle=hydrate_precommit_bundle,
        bootstrap_empty_repo=bootstrap_empty_repo,
    )
