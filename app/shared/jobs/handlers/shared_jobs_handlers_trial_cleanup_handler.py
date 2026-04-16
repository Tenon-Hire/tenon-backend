"""Application module for jobs handlers trial cleanup handler workflows."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.shared.database import async_session_maker
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
    Workspace,
    WorkspaceGroup,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_handler import (
    _apply_retention_cleanup,
    _enforce_collaborator_revocation,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_processing_handler import (
    _process_cleanup_target,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_queries_handler import (
    _load_sessions_with_cutoff,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_runner_handler import (
    _resolve_cleanup_config,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    _WorkspaceCleanupTarget,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _cleanup_target_repo_key,
    _normalize_datetime,
    _parse_positive_int,
)
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)
from app.trials.services.trials_services_trials_cleanup_jobs_service import (
    TRIAL_CLEANUP_JOB_TYPE,
)

logger = logging.getLogger(__name__)


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


async def _list_trial_cleanup_targets(
    db, *, trial_id: int
) -> list[_WorkspaceCleanupTarget]:
    grouped_rows = (
        await db.execute(
            select(WorkspaceGroup, CandidateSession, Trial)
            .join(
                CandidateSession,
                CandidateSession.id == WorkspaceGroup.candidate_session_id,
            )
            .join(Trial, Trial.id == CandidateSession.trial_id)
            .where(Trial.id == trial_id)
            .order_by(WorkspaceGroup.created_at.asc(), WorkspaceGroup.id.asc())
        )
    ).all()
    legacy_rows = (
        await db.execute(
            select(Workspace, CandidateSession, Trial)
            .join(
                CandidateSession, CandidateSession.id == Workspace.candidate_session_id
            )
            .join(Trial, Trial.id == CandidateSession.trial_id)
            .where(Trial.id == trial_id, Workspace.workspace_group_id.is_(None))
            .order_by(Workspace.created_at.asc(), Workspace.id.asc())
        )
    ).all()

    targets: list[_WorkspaceCleanupTarget] = []
    seen_repo_keys: set[tuple[int, str]] = set()
    for record, candidate_session, trial in [*grouped_rows, *legacy_rows]:
        fallback_prefix = (
            "workspace_group" if isinstance(record, WorkspaceGroup) else "workspace"
        )
        repo_key = _cleanup_target_repo_key(
            candidate_session_id=candidate_session.id,
            repo_full_name=record.repo_full_name,
            fallback_id=f"{fallback_prefix}:{record.id}",
        )
        if repo_key in seen_repo_keys:
            continue
        seen_repo_keys.add(repo_key)
        targets.append(
            _WorkspaceCleanupTarget(
                record=record,
                candidate_session=candidate_session,
                trial=trial,
            )
        )

    targets.sort(
        key=lambda target: (
            _normalize_datetime(target.record.created_at),
            str(target.record.id),
        )
    )
    return targets


async def _process_terminated_trial_cleanup_target(
    *,
    db,
    target: _WorkspaceCleanupTarget,
    now: datetime,
    config,
    github_client,
    cutoff_session_ids: set[int],
    summary: dict[str, int],
    job_id: str | None,
    logger,
) -> None:
    immediate_config = replace(config, retention_days=0)
    await _process_cleanup_target(
        db=db,
        target=target,
        now=now,
        config=immediate_config,
        github_client=github_client,
        cutoff_session_ids=cutoff_session_ids,
        summary=summary,
        job_id=job_id,
        logger=logger,
        enforce_collaborator_revocation=_enforce_collaborator_revocation,
        apply_retention_cleanup=_apply_retention_cleanup,
    )


async def handle_trial_cleanup(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Handle trial cleanup."""
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

        targets = await _list_trial_cleanup_targets(db, trial_id=trial_id)
        config = _resolve_cleanup_config()
        github_client = get_github_client()
        candidate_session_ids = sorted(
            {target.candidate_session.id for target in targets}
        )
        cutoff_session_ids = await _load_sessions_with_cutoff(
            db,
            candidate_session_ids=candidate_session_ids,
        )
        summary: dict[str, int] = {
            "candidateCount": len(targets),
            "processed": 0,
            "revoked": 0,
            "archived": 0,
            "deleted": 0,
            "failed": 0,
            "pending": 0,
            "alreadyCleaned": 0,
            "skippedActive": 0,
        }

        job_id = str(_parse_positive_int(payload_json.get("jobId")) or "")
        job_id = job_id or None
        now = datetime.now(UTC)
        for target in targets:
            await _process_terminated_trial_cleanup_target(
                db=db,
                target=target,
                now=now,
                config=config,
                github_client=github_client,
                cutoff_session_ids=cutoff_session_ids,
                summary=summary,
                job_id=job_id,
                logger=logger,
            )

        return {
            "status": "completed",
            "trialId": trial_id,
            **summary,
        }


__all__ = [
    "TRIAL_CLEANUP_JOB_TYPE",
    "handle_trial_cleanup",
]
