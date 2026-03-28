from __future__ import annotations

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


def test_validate_and_decode_helpers():
    assert template_health._validate_test_results_schema(
        {"passed": 1, "failed": 0, "total": 1, "stdout": "", "stderr": ""}
    )
    assert template_health._validate_test_results_schema({"passed": True}) is False
    assert (
        template_health._validate_test_results_schema(
            {"passed": 1, "failed": 0, "total": 1, "stdout": 1, "stderr": ""}
        )
        is False
    )
    assert (
        template_health._validate_test_results_schema(
            {
                "passed": 1,
                "failed": 0,
                "total": 1,
                "stdout": "",
                "stderr": "",
                "summary": "bad",
            }
        )
        is False
    )
    assert (
        template_health._decode_contents({"content": "bad", "encoding": "base64"})
        is None
    )
    assert template_health._decode_contents({"content": "plain"}) == "plain"
    assert template_health._decode_contents({}) is None
    assert template_health._decode_contents({"content": b"bytes"}) is None
    assert template_health._extract_test_results_json(b"badzip") is None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{template_health.TEST_ARTIFACT_NAMESPACE}.json", "{not json")
    assert template_health._extract_test_results_json(buf.getvalue()) is None
    errors, _ = template_health.workflow_contract_errors("missing")
    assert "workflow_missing_upload_artifact" in errors
    assert (
        template_health._classify_github_error(GithubError("x", status_code=403))
        == "github_forbidden"
    )
    run = WorkflowRun(
        id=1,
        status="completed",
        conclusion="success",
        html_url="",
        head_sha="",
        event="workflow_dispatch",
        created_at="not-a-date",
    )
    assert template_health._is_dispatched_run(run, datetime.now(UTC)) is False
