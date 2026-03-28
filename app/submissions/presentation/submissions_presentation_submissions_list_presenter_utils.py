"""Application module for submissions presentation submissions list presenter utils workflows."""

from __future__ import annotations

from app.submissions.presentation.submissions_presentation_submissions_commit_basis_utils import (
    resolve_commit_basis,
)
from app.submissions.presentation.submissions_presentation_submissions_links_utils import (
    build_diff_url,
    build_links,
)
from app.submissions.presentation.submissions_presentation_submissions_output_utils import (
    max_output_chars,
    parse_diff_summary,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_utils import (
    build_test_results,
)
from app.submissions.services import service_recruiter as recruiter_sub_service


def present_list_item(sub, task, *, day_audit=None):
    """Present list item."""
    parsed_output = recruiter_sub_service.parse_test_output(
        getattr(sub, "test_output", None)
    )
    diff_summary = parse_diff_summary(sub.diff_summary_json)
    repo_full_name = sub.code_repo_path
    commit_sha, cutoff_commit_sha, cutoff_at, eval_basis_ref = resolve_commit_basis(
        sub, day_audit
    )
    commit_url, workflow_url = build_links(
        repo_full_name, commit_sha, sub.workflow_run_id
    )
    if commit_url is None:
        fallback_commit_sha = getattr(sub, "commit_sha", None)
        if repo_full_name and fallback_commit_sha:
            commit_url = (
                f"https://github.com/{repo_full_name}/commit/{fallback_commit_sha}"
            )
    diff_url = build_diff_url(repo_full_name, diff_summary)
    test_results = build_test_results(
        sub,
        parsed_output,
        workflow_url=workflow_url,
        commit_url=commit_url,
        include_output=False,
        max_output_chars=max_output_chars(False),
        commit_sha_override=commit_sha,
    )
    if test_results is not None and commit_url and not test_results.get("commitUrl"):
        test_results["commitUrl"] = commit_url
    if (
        test_results is not None
        and workflow_url
        and not test_results.get("workflowUrl")
    ):
        test_results["workflowUrl"] = workflow_url
    return {
        "submissionId": sub.id,
        "candidateSessionId": sub.candidate_session_id,
        "taskId": sub.task_id,
        "dayIndex": task.day_index,
        "type": task.type,
        "submittedAt": sub.submitted_at,
        "repoFullName": repo_full_name,
        "repoUrl": f"https://github.com/{repo_full_name}" if repo_full_name else None,
        "workflowRunId": sub.workflow_run_id,
        "commitSha": commit_sha,
        "cutoffCommitSha": cutoff_commit_sha,
        "cutoffAt": cutoff_at,
        "evalBasisRef": eval_basis_ref,
        "workflowUrl": workflow_url,
        "commitUrl": commit_url,
        "diffUrl": diff_url,
        "diffSummary": diff_summary,
        "testResults": test_results,
    }
