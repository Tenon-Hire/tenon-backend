from __future__ import annotations

# NOTE: Kept together (>50 LOC) to keep the submit path readable across validation, Actions dispatch, and diff summarization.
import json
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession
from app.domains.candidate_sessions import service as cs_service
from app.domains.github_native.client import GithubClient, GithubError
from app.domains.submissions import service_candidate as submission_service
from app.domains.submissions.exceptions import WorkspaceMissing
from app.domains.submissions.rate_limits import apply_rate_limit
from app.infra.errors import ApiError


async def submit_task(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    payload,
    github_client: GithubClient,
    actions_runner,
):
    """Handle submission creation, including optional GitHub Actions run."""
    apply_rate_limit(candidate_session.id, "submit")
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    await submission_service.ensure_not_duplicate(db, candidate_session.id, task_id)

    _, _, current_task, *_ = await cs_service.progress_snapshot(db, candidate_session)
    submission_service.ensure_in_order(current_task, task_id)
    submission_service.validate_submission_payload(task, payload)

    now = datetime.now(UTC)
    actions_result = diff_summary_json = None
    workspace = None

    if submission_service.is_code_task(task):
        workspace = await submission_service.workspace_repo.get_by_session_and_task(
            db, candidate_session_id=candidate_session.id, task_id=task.id
        )
        if workspace is None:
            raise WorkspaceMissing()
        branch = submission_service.validate_branch(
            getattr(payload, "branch", None) or workspace.default_branch or "main"
        )
        try:
            actions_result = await submission_service.run_actions_tests(
                runner=actions_runner,
                workspace=workspace,
                branch=branch or "main",
                workflow_inputs=getattr(payload, "workflowInputs", None),
            )
            await submission_service.record_run_result(db, workspace, actions_result)
            if actions_result.head_sha:
                base_sha = workspace.base_template_sha or branch
                compare = await github_client.get_compare(
                    workspace.repo_full_name, base_sha, actions_result.head_sha
                )
                diff_summary_json = json.dumps(
                    submission_service.summarize_diff(
                        compare, base=base_sha, head=actions_result.head_sha
                    ),
                    ensure_ascii=False,
                )
        except GithubError:
            raise
        except Exception as exc:  # pragma: no cover - safety net
            raise ApiError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub unavailable. Please try again.",
                error_code="GITHUB_UNAVAILABLE",
                retryable=True,
            ) from exc

    submission = await submission_service.create_submission(
        db,
        candidate_session,
        task,
        payload,
        now=now,
        actions_result=actions_result,
        workspace=workspace,
        diff_summary_json=diff_summary_json,
    )
    completed, total, is_complete = await submission_service.progress_after_submission(
        db, candidate_session, now=now
    )
    return task, submission, completed, total, is_complete
