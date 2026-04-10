from __future__ import annotations

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


def test_workflow_contract_errors_missing_json():
    content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: winoe-test-results",
            "path: artifacts/results.txt",
        ]
    )
    errors, checks = workflow_contract_errors(content)
    assert "workflow_missing_test_results_json" in errors
    assert checks["workflowHasUploadArtifact"] is True
    assert checks["workflowHasArtifactName"] is True
    assert checks["workflowHasTestResultsJson"] is False
