from types import SimpleNamespace

from app.shared.http.routes import submissions


def test_build_test_results_empty_parsed_payload_stays_none():
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
            parsed_output={},
            workflow_url=None,
            commit_url=None,
            include_output=True,
            max_output_chars=5,
        )
        is None
    )


def test_build_test_results_sets_timeout_from_conclusion():
    sub = SimpleNamespace(
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        workflow_run_id="55",
        commit_sha=None,
        last_run_at=None,
    )
    parsed_output = {
        "passed": 0,
        "failed": 1,
        "total": 1,
        "conclusion": "timed_out",
        "stdout": "",
        "stderr": "",
    }
    result = submissions._build_test_results(
        sub,
        parsed_output,
        workflow_url=None,
        commit_url=None,
        include_output=True,
        max_output_chars=10,
    )
    assert result["timeout"] is True


def test_build_test_results_uses_db_conclusion_for_timeout():
    sub = SimpleNamespace(
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        workflow_run_id="88",
        commit_sha="c1",
        last_run_at=None,
        workflow_run_conclusion="TIMED_OUT",
    )
    result = submissions._build_test_results(
        sub,
        parsed_output=None,
        workflow_url=None,
        commit_url=None,
        include_output=False,
        max_output_chars=5,
    )
    assert result["timeout"] is True


def test_build_test_results_infers_timeout_from_conclusion_only():
    sub = SimpleNamespace(
        tests_passed=None,
        tests_failed=None,
        test_output=None,
        workflow_run_id="77",
        commit_sha=None,
        last_run_at=None,
        workflow_run_conclusion="timed_out",
    )
    result = submissions._build_test_results(
        sub,
        parsed_output=None,
        workflow_url=None,
        commit_url=None,
        include_output=False,
        max_output_chars=5,
    )
    assert result["timeout"] is True
    assert result["conclusion"] == "timed_out"
