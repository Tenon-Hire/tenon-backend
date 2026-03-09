from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.candidate_sessions import candidate_session_from_headers
from app.core.db import get_session
from app.domains import CandidateSession
from app.domains.candidate_sessions import repository as cs_repo
from app.domains.submissions.schemas import CodespaceStatusResponse
from app.domains.submissions.use_cases.codespace_status import codespace_status

router = APIRouter()


@router.get(
    "/{task_id}/codespace/status",
    response_model=CodespaceStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def codespace_status_route(
    task_id: Annotated[int, Path(..., ge=1)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CodespaceStatusResponse:
    """Return Codespace details and last known test status for a task."""
    workspace, last_test_summary, codespace_url, task = await codespace_status(
        db, candidate_session=candidate_session, task_id=task_id
    )
    day_audit = await cs_repo.get_day_audit(
        db,
        candidate_session_id=candidate_session.id,
        day_index=task.day_index,
    )
    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)

    return CodespaceStatusResponse(
        repoFullName=workspace.repo_full_name,
        repoUrl=f"https://github.com/{workspace.repo_full_name}",
        codespaceUrl=codespace_url,
        defaultBranch=workspace.default_branch,
        latestCommitSha=workspace.latest_commit_sha,
        lastWorkflowRunId=workspace.last_workflow_run_id,
        lastWorkflowConclusion=workspace.last_workflow_conclusion,
        lastTestSummary=last_test_summary,
        workspaceId=workspace.id,
        cutoffCommitSha=cutoff_commit_sha,
        cutoffAt=cutoff_at,
    )
