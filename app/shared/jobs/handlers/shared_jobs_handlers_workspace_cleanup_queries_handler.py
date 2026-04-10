"""Application module for jobs handlers workspace cleanup queries handler workflows."""

from __future__ import annotations

from sqlalchemy import select

from app.shared.database.shared_database_models_model import (
    CandidateDayAudit,
    CandidateSession,
    Trial,
    Workspace,
    WorkspaceGroup,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    _WorkspaceCleanupTarget,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _cleanup_target_repo_key,
    _normalize_datetime,
)


async def _list_company_cleanup_targets(
    db, *, company_id: int
) -> list[_WorkspaceCleanupTarget]:
    grouped_rows = (
        await db.execute(
            select(WorkspaceGroup, CandidateSession, Trial)
            .join(
                CandidateSession,
                CandidateSession.id == WorkspaceGroup.candidate_session_id,
            )
            .join(Trial, Trial.id == CandidateSession.trial_id)
            .where(Trial.company_id == company_id)
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
            .where(
                Trial.company_id == company_id,
                Workspace.workspace_group_id.is_(None),
            )
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


async def _load_sessions_with_cutoff(
    db, *, candidate_session_ids: list[int]
) -> set[int]:
    if not candidate_session_ids:
        return set()
    rows = (
        await db.execute(
            select(CandidateDayAudit.candidate_session_id)
            .where(CandidateDayAudit.candidate_session_id.in_(candidate_session_ids))
            .distinct()
        )
    ).scalars()
    return {int(value) for value in rows}


__all__ = ["_list_company_cleanup_targets", "_load_sessions_with_cutoff"]
