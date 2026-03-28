"""Application module for tasks routes tasks run response utils workflows."""

from app.integrations.github.actions_runner import ActionsRunResult
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    RunTestsResponse,
)


def build_run_response(result: ActionsRunResult) -> RunTestsResponse:
    """Render a workflow run result into API response shape."""
    return RunTestsResponse(
        status=result.status,
        passed=result.passed,
        failed=result.failed,
        total=result.total,
        stdout=result.stdout,
        stderr=result.stderr,
        timeout=result.conclusion == "timed_out",
        runId=result.run_id,
        conclusion=result.conclusion,
        workflowUrl=result.html_url,
        commitSha=result.head_sha,
        pollAfterMs=result.poll_after_ms,
    )
