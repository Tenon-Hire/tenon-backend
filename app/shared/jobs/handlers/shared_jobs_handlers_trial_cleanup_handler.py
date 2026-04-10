"""Application module for jobs handlers trial cleanup handler workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.shared.database import async_session_maker
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
    Workspace,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)
from app.trials.services.trials_services_trials_cleanup_jobs_service import (
    TRIAL_CLEANUP_JOB_TYPE,
)


def _parse_trial_id(payload_json: dict[str, Any]) -> int | None:
    raw_value = payload_json.get("trialId")
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return raw_value if raw_value > 0 else None
    if isinstance(raw_value, str) and raw_value.isdigit():
        parsed = int(raw_value)
        return parsed if parsed > 0 else None
    return None


async def handle_trial_cleanup(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Retry-safe no-op cleanup skeleton scoped to trial-owned resources."""
    trial_id = _parse_trial_id(payload_json)
    if trial_id is None:
        return {"status": "skipped_invalid_payload", "trialId": None}

    async with async_session_maker() as db:
        trial = (
            await db.execute(select(Trial).where(Trial.id == trial_id))
        ).scalar_one_or_none()
        if trial is None:
            return {"status": "trial_not_found", "trialId": trial_id}
        if trial.status != TRIAL_STATUS_TERMINATED:
            return {
                "status": "skipped_not_terminated",
                "trialId": trial_id,
            }

        rows = (
            await db.execute(
                select(Workspace.repo_full_name, Workspace.template_repo_full_name)
                .join(
                    CandidateSession,
                    CandidateSession.id == Workspace.candidate_session_id,
                )
                .where(CandidateSession.trial_id == trial_id)
            )
        ).all()

    protected_template_repo_matches = sum(
        1 for repo_full_name, template_repo in rows if repo_full_name == template_repo
    )
    return {
        "status": "noop",
        "trialId": trial_id,
        "workspaceRepoCount": len(rows),
        "protectedTemplateRepoMatches": protected_template_repo_matches,
    }


__all__ = [
    "TRIAL_CLEANUP_JOB_TYPE",
    "handle_trial_cleanup",
]
