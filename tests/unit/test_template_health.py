from app.domains.github_native.template_health import workflow_contract_errors


def test_workflow_contract_errors_ok():
    content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: tenon-test-results",
            "path: artifacts/tenon-test-results.json",
        ]
    )
    errors, checks = workflow_contract_errors(content)
    assert errors == []
    assert checks["workflowHasUploadArtifact"] is True
    assert checks["workflowHasArtifactName"] is True
    assert checks["workflowHasTestResultsJson"] is True


def test_workflow_contract_errors_missing_json():
    content = "\n".join(
        [
            "uses: actions/upload-artifact@v4",
            "name: tenon-test-results",
            "path: artifacts/results.txt",
        ]
    )
    errors, checks = workflow_contract_errors(content)
    assert "workflow_missing_test_results_json" in errors
    assert checks["workflowHasUploadArtifact"] is True
    assert checks["workflowHasArtifactName"] is True
    assert checks["workflowHasTestResultsJson"] is False
