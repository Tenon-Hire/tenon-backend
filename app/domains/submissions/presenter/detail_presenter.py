from __future__ import annotations

from app.domains.submissions import service_recruiter as recruiter_sub_service
from app.domains.submissions.presenter.links import build_diff_url, build_links
from app.domains.submissions.presenter.output import max_output_chars, parse_diff_summary
from app.domains.submissions.presenter.test_results import build_test_results


def present_detail(sub, task, cs, sim):
    _ = sim
    parsed_output = recruiter_sub_service.parse_test_output(getattr(sub, "test_output", None))
    diff_summary = parse_diff_summary(sub.diff_summary_json)
    repo_full_name = sub.code_repo_path
    commit_url, workflow_url = build_links(repo_full_name, sub.commit_sha, sub.workflow_run_id)
    diff_url = build_diff_url(repo_full_name, diff_summary)
    test_results = build_test_results(
        sub,
        parsed_output,
        workflow_url=workflow_url,
        commit_url=commit_url,
        include_output=True,
        max_output_chars=max_output_chars(True),
    )
    return {
        "submissionId": sub.id,
        "candidateSessionId": cs.id,
        "task": {
            "taskId": task.id,
            "dayIndex": task.day_index,
            "type": task.type,
            "title": getattr(task, "title", None),
            "prompt": getattr(task, "prompt", None),
        },
        "contentText": sub.content_text,
        "code": (
            {
                "repoPath": sub.code_repo_path,
                "repoFullName": sub.code_repo_path,
                "repoUrl": f"https://github.com/{sub.code_repo_path}" if sub.code_repo_path else None,
            }
            if sub.code_repo_path is not None
            else None
        ),
        "testResults": test_results,
        "diffSummary": diff_summary,
        "submittedAt": sub.submitted_at,
        "workflowUrl": workflow_url,
        "commitUrl": commit_url,
        "diffUrl": diff_url,
    }
