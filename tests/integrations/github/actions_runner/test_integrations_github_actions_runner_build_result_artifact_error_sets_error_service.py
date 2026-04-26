from __future__ import annotations

import pytest

from tests.integrations.github.actions_runner.test_integrations_github_actions_runner_utils import *


@pytest.mark.asyncio
async def test_build_result_artifact_error_sets_error(monkeypatch):
    runner = GithubActionsRunner(
        GithubClient(base_url="x", token="y"), workflow_file="wf"
    )

    async def fake_parse(repo, run_id):
        return None, "artifact_missing"

    monkeypatch.setattr(runner, "_parse_artifacts", fake_parse)
    run = WorkflowRun(
        id=1,
        status="completed",
        conclusion="success",
        html_url=None,
        head_sha=None,
        artifact_count=0,
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat(),
    )
    result = await runner._build_result("org/repo", run)
    assert result.status == "error"
    assert "artifact_error" in result.raw


@pytest.mark.asyncio
async def test_build_result_surfaces_evidence_summary_when_artifacts_missing():
    class EvidenceOnlyClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="x", token="y")

        async def list_artifacts(self, *_args, **_kwargs):
            return [{"id": 11, "name": "winoe-commit-metadata"}]

        async def download_artifact_zip(self, *_args, **_kwargs):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr(
                    "commit_metadata.json",
                    json.dumps(
                        {
                            "schema_version": "1",
                            "repository_full_name": "org/repo",
                            "commit_sha": "abc123",
                            "workflow_run_id": "11",
                            "generated_at": "2026-03-13T00:00:00Z",
                            "status": "success",
                            "payload": {
                                "generatedAt": "2026-03-13T00:00:00Z",
                                "commits": [],
                            },
                        }
                    ),
                )
            return buf.getvalue()

    runner = GithubActionsRunner(EvidenceOnlyClient(), workflow_file="wf")
    run = WorkflowRun(
        id=1,
        status="completed",
        conclusion="success",
        html_url=None,
        head_sha=None,
        artifact_count=1,
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat(),
    )
    result = await runner._build_result("org/repo", run)
    assert result.status == "error"
    assert result.raw is not None
    assert result.raw["artifact_error"] == "artifact_missing"
    assert (
        result.raw["summary"]["evidenceArtifacts"]["commitMetadata"]["artifactId"] == 11
    )


@pytest.mark.asyncio
async def test_build_result_surfaces_evidence_summary_when_test_results_corrupt():
    class CorruptResultsClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="x", token="y")

        async def list_artifacts(self, *_args, **_kwargs):
            return [
                {"id": 21, "name": "winoe-test-results"},
                {"id": 22, "name": "winoe-commit-metadata"},
            ]

        async def download_artifact_zip(self, _repo_full_name: str, artifact_id: int):
            if artifact_id == 21:
                return b"not-a-zip"
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr(
                    "commit_metadata.json",
                    json.dumps(
                        {
                            "schema_version": "1",
                            "repository_full_name": "org/repo",
                            "commit_sha": "abc123",
                            "workflow_run_id": "11",
                            "generated_at": "2026-03-13T00:00:00Z",
                            "status": "success",
                            "payload": {
                                "generatedAt": "2026-03-13T00:00:00Z",
                                "commits": [],
                            },
                        }
                    ),
                )
            return buf.getvalue()

    runner = GithubActionsRunner(CorruptResultsClient(), workflow_file="wf")
    run = WorkflowRun(
        id=2,
        status="completed",
        conclusion="success",
        html_url=None,
        head_sha=None,
        artifact_count=2,
        event="workflow_dispatch",
        created_at=datetime.now(UTC).isoformat(),
    )
    result = await runner._build_result("org/repo", run)
    assert result.status == "error"
    assert result.raw is not None
    assert result.raw["artifact_error"] == "artifact_corrupt"
    assert (
        result.raw["summary"]["evidenceArtifacts"]["commitMetadata"]["artifactId"] == 22
    )
