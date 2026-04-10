from datetime import UTC, datetime
from types import SimpleNamespace

from app.shared.http.routes import submissions


def test_build_test_results_returns_none_when_empty():
    sub = SimpleNamespace(
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        workflow_run_id=None,
        commit_sha=None,
        last_run_at=None,
    )
    assert (
        submissions._build_test_results(
            sub,
            parsed_output=None,
            workflow_url=None,
            commit_url=None,
            include_output=True,
            max_output_chars=10,
        )
        is None
    )


def test_build_test_results_redacts_tokens_and_marks_timeout():
    sub = SimpleNamespace(
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        workflow_run_id="999",
        commit_sha="abc123",
        last_run_at=None,
    )
    parsed_output = {
        "passed": 0,
        "failed": 1,
        "total": 1,
        "stdout": "ghp_ABCDEF1234567890",
        "stderr": "github_pat_ABC1234567890",
        "conclusion": "timed_out",
    }
    result = submissions._build_test_results(
        sub,
        parsed_output,
        workflow_url="https://example.com/run/1",
        commit_url="https://example.com/commit/abc123",
        include_output=True,
        max_output_chars=9,
    )
    assert result["status"] == "failed"
    assert result["timeout"] is True
    assert result["artifactName"] == "winoe-test-results"
    assert result["stdoutTruncated"] is True
    assert result["stderrTruncated"] is True
    assert "[redacted" in (result["output"]["stdout"] or "")
    assert "[redacted" in (result["output"]["stderr"] or "")


def test_build_test_results_uses_db_status_and_artifact_error():
    sub = SimpleNamespace(
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        workflow_run_id="77",
        commit_sha="abc123",
        last_run_at=datetime.now(UTC),
        workflow_run_status="COMPLETED",
        workflow_run_conclusion="TIMED_OUT",
    )
    parsed_output = {"artifactErrorCode": "MISSING", "stdout": "ok", "stderr": "err"}
    result = submissions._build_test_results(
        sub,
        parsed_output,
        workflow_url="https://example.com/run/77",
        commit_url="https://example.com/commit/abc123",
        include_output=False,
        max_output_chars=50,
    )
    assert result["runStatus"] == "completed"
    assert result["conclusion"] == "timed_out"
    assert result["timeout"] is False
    assert result["artifactErrorCode"] == "missing"
