import json

import pytest
from fastapi import HTTPException

from app.domain.submissions import service_candidate, service_recruiter
from app.services.sandbox_client import SandboxRunResult


def test_serialize_sandbox_result_produces_json_and_counts():
    result = SandboxRunResult(
        status="failed",
        passed=1,
        failed=2,
        total=3,
        stdout="out",
        stderr="err",
        duration_ms=None,
        raw=None,
    )
    payload = service_candidate.serialize_sandbox_result(result)

    assert payload["tests_passed"] == 1
    assert payload["tests_failed"] == 2
    assert payload["last_run_at"] is not None
    parsed = json.loads(payload["test_output"])
    assert parsed["status"] == "failed"
    assert parsed["passed"] == 1
    assert parsed["failed"] == 2
    assert parsed["total"] == 3
    assert parsed["stdout"] == "out"
    assert parsed["stderr"] == "err"
    assert parsed["timeout"] is False


def test_validate_run_payload_rejects_non_code_task():
    class DummyTask:
        type = "design"

    dummy_payload = type("p", (), {"codeBlob": "x", "files": None})
    with pytest.raises(HTTPException) as exc:
        service_candidate.validate_run_payload(DummyTask(), dummy_payload)
    assert exc.value.status_code == 400


def test_parse_test_output_handles_json_and_fallback():
    raw = json.dumps({"status": "passed", "passed": 1, "failed": 0})
    parsed = service_recruiter.parse_test_output(raw)
    assert isinstance(parsed, dict)
    assert parsed["status"] == "passed"

    non_json = "stdout:\nhello"
    assert service_recruiter.parse_test_output(non_json) == non_json
