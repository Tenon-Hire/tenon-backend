from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import submissions
from tests.factories import create_recruiter


def test_derive_test_status_variants():
    assert submissions._derive_test_status(None, None, None) is None
    assert submissions._derive_test_status(None, 1, "oops") == "failed"
    assert submissions._derive_test_status(2, 0, "ok") == "passed"
    assert submissions._derive_test_status(None, None, "  logs  ") == "unknown"


@pytest.mark.asyncio
async def test_get_submission_detail_not_found(async_session):
    user = await create_recruiter(async_session, email="missing-sub@sim.com")
    with pytest.raises(HTTPException) as exc:
        await submissions.get_submission_detail(
            submission_id=9999, db=async_session, user=user
        )
    assert exc.value.status_code == 404


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
    assert result["artifactName"] == "tenon-test-results"
    assert result["stdoutTruncated"] is True
    assert result["stderrTruncated"] is True
    assert "[redacted" in (result["output"]["stdout"] or "")
    assert "[redacted" in (result["output"]["stderr"] or "")
