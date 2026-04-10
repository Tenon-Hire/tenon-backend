from __future__ import annotations

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


def test_workflow_contract_errors_ok():
    content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: winoe-test-results",
            "path: artifacts/winoe-test-results.json",
        ]
    )
    errors, checks = workflow_contract_errors(content)
    assert errors == []
    assert checks["workflowHasUploadArtifact"] is True
    assert checks["workflowHasArtifactName"] is True
    assert checks["workflowHasTestResultsJson"] is True
