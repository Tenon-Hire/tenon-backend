from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta
from zipfile import ZipFile

import pytest

from app.integrations.github.actions_runner import GithubActionsRunner
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifacts_service import (
    _collect_evidence_artifacts,
    _parse_first_test_artifact,
    _pick_test_artifacts,
)
from app.integrations.github.client import GithubClient, GithubError, WorkflowRun


class DummyClient(GithubClient):
    def __init__(self):
        super().__init__(base_url="https://api.github.com", token="x")


class StubClient(GithubClient):
    def __init__(self, artifacts, contents):
        super().__init__(base_url="https://api.github.com", token="x")
        self._artifacts = artifacts
        self._contents = contents

    async def list_artifacts(self, repo_full_name: str, run_id: int):
        return self._artifacts

    async def download_artifact_zip(self, repo_full_name: str, artifact_id: int):
        return self._contents[artifact_id]


def _wrap_artifact_payload(payload):
    return {
        "schema_version": "1",
        "repository_full_name": "org/repo",
        "commit_sha": "abc123",
        "workflow_run_id": "11",
        "generated_at": "2026-03-13T00:00:00Z",
        "status": "success",
        "payload": payload,
    }


def test_is_dispatched_run_filters_event_and_created_at():
    runner = GithubActionsRunner(
        DummyClient(), workflow_file="winoe-evidence-capture.yml"
    )
    dispatch_at = datetime.now(UTC)
    recent_run = WorkflowRun(
        id=1,
        status="completed",
        conclusion="success",
        html_url="",
        head_sha="abc",
        artifact_count=0,
        event="workflow_dispatch",
        created_at=(dispatch_at - timedelta(seconds=5)).isoformat(),
    )
    old_run = WorkflowRun(
        id=2,
        status="completed",
        conclusion="success",
        html_url="",
        head_sha="def",
        artifact_count=0,
        event="workflow_dispatch",
        created_at=(dispatch_at - timedelta(seconds=30)).isoformat(),
    )
    assert runner._is_dispatched_run(recent_run, dispatch_at) is True
    assert runner._is_dispatched_run(old_run, dispatch_at) is False


@pytest.mark.asyncio
async def test_parse_artifacts_prefers_named():
    preferred_buf = io.BytesIO()
    with ZipFile(preferred_buf, "w") as zf:
        zf.writestr("winoe-test-results.json", '{"passed":5,"failed":1,"total":6}')
    other_buf = io.BytesIO()
    with ZipFile(other_buf, "w") as zf:
        zf.writestr("other.json", '{"passed":1,"failed":0,"total":1}')
    client = StubClient(
        artifacts=[
            {"id": 1, "name": "unrelated"},
            {"id": 2, "name": "winoe-test-results"},
        ],
        contents={1: other_buf.getvalue(), 2: preferred_buf.getvalue()},
    )
    runner = GithubActionsRunner(client, workflow_file="winoe-evidence-capture.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 10)
    assert error is None
    assert parsed
    assert parsed.passed == 5
    assert parsed.failed == 1
    assert parsed.total == 6


@pytest.mark.asyncio
async def test_parse_artifacts_surfaces_evidence_artifacts():
    test_buf = io.BytesIO()
    with ZipFile(test_buf, "w") as zf:
        zf.writestr(
            "winoe-test-results.json",
            json.dumps(
                {
                    "passed": 2,
                    "failed": 0,
                    "total": 2,
                    "summary": {"detectedTool": "pytest"},
                }
            ),
        )
        zf.writestr(
            "test_results.json",
            json.dumps(
                _wrap_artifact_payload(
                    {"status": "success", "command": "python -m pytest"}
                )
            ),
        )

    commit_buf = io.BytesIO()
    with ZipFile(commit_buf, "w") as zf:
        zf.writestr(
            "commit_metadata.json",
            json.dumps(
                _wrap_artifact_payload(
                    {"generatedAt": "2026-03-13T00:00:00Z", "commits": []}
                )
            ),
        )

    timeline_buf = io.BytesIO()
    with ZipFile(timeline_buf, "w") as zf:
        zf.writestr(
            "file_creation_timeline.json",
            json.dumps(
                _wrap_artifact_payload(
                    {"generatedAt": "2026-03-13T00:00:00Z", "filesCreated": []}
                )
            ),
        )

    snapshot_buf = io.BytesIO()
    with ZipFile(snapshot_buf, "w") as zf:
        zf.writestr(
            "repo_tree_summary.json",
            json.dumps(
                _wrap_artifact_payload(
                    {"generatedAt": "2026-03-13T00:00:00Z", "paths": ["src/app.py"]}
                )
            ),
        )
        zf.writestr("repo_tree_summary.txt", "src/app.py\n")

    dependency_buf = io.BytesIO()
    with ZipFile(dependency_buf, "w") as zf:
        zf.writestr(
            "dependency_manifests.json",
            json.dumps(
                _wrap_artifact_payload(
                    {"generatedAt": "2026-03-13T00:00:00Z", "manifests": []}
                )
            ),
        )

    test_detection_buf = io.BytesIO()
    with ZipFile(test_detection_buf, "w") as zf:
        zf.writestr(
            "test_detection.json",
            json.dumps(
                _wrap_artifact_payload(
                    {
                        "detected": True,
                        "command": "python -m pytest",
                        "reason": "detected from pyproject.toml",
                    }
                )
            ),
        )

    lint_detection_buf = io.BytesIO()
    with ZipFile(lint_detection_buf, "w") as zf:
        zf.writestr(
            "lint_detection.json",
            json.dumps(
                _wrap_artifact_payload(
                    {
                        "detected": True,
                        "command": "python -m ruff check .",
                        "reason": "detected from pyproject.toml",
                    }
                )
            ),
        )

    lint_buf = io.BytesIO()
    with ZipFile(lint_buf, "w") as zf:
        zf.writestr(
            "lint_results.json",
            json.dumps(
                _wrap_artifact_payload(
                    {"status": "success", "command": "python -m ruff check ."}
                )
            ),
        )

    evidence_manifest_buf = io.BytesIO()
    with ZipFile(evidence_manifest_buf, "w") as zf:
        zf.writestr(
            "evidence_manifest.json",
            json.dumps(_wrap_artifact_payload({"artifacts": ["commit_metadata.json"]})),
        )

    client = StubClient(
        artifacts=[
            {"id": 1, "name": "winoe-test-results"},
            {"id": 2, "name": "winoe-commit-metadata"},
            {"id": 3, "name": "winoe-file-creation-timeline"},
            {"id": 4, "name": "winoe-repo-tree-summary"},
            {"id": 5, "name": "winoe-dependency-manifests"},
            {"id": 6, "name": "winoe-test-detection"},
            {"id": 7, "name": "winoe-lint-detection"},
            {"id": 8, "name": "winoe-lint-results"},
            {"id": 9, "name": "winoe-evidence-manifest"},
        ],
        contents={
            1: test_buf.getvalue(),
            2: commit_buf.getvalue(),
            3: timeline_buf.getvalue(),
            4: snapshot_buf.getvalue(),
            5: dependency_buf.getvalue(),
            6: test_detection_buf.getvalue(),
            7: lint_detection_buf.getvalue(),
            8: lint_buf.getvalue(),
            9: evidence_manifest_buf.getvalue(),
        },
    )
    runner = GithubActionsRunner(client, workflow_file="winoe-evidence-capture.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 11)

    assert error is None
    assert parsed is not None
    assert parsed.summary is not None
    evidence = parsed.summary["evidenceArtifacts"]
    assert evidence["commitMetadata"]["data"]["schema_version"] == "1"
    assert evidence["commitMetadata"]["data"]["repository_full_name"] == "org/repo"
    assert (
        evidence["commitMetadata"]["data"]["payload"]["generatedAt"]
        == "2026-03-13T00:00:00Z"
    )
    assert evidence["fileCreationTimeline"]["data"]["payload"]["filesCreated"] == []
    assert evidence["repoTreeSummary"]["data"]["payload"]["paths"] == ["src/app.py"]
    assert (
        evidence["repoTreeSummary"]["textFiles"]["repo_tree_summary.txt"]
        == "src/app.py\n"
    )
    assert evidence["dependencyManifests"]["data"]["payload"]["manifests"] == []
    assert evidence["testDetection"]["data"]["payload"]["command"] == "python -m pytest"
    assert evidence["testResults"]["data"]["payload"]["command"] == "python -m pytest"
    assert (
        evidence["lintDetection"]["data"]["payload"]["command"]
        == "python -m ruff check ."
    )
    assert evidence["lintResults"]["data"]["payload"]["status"] == "success"
    assert evidence["evidenceManifest"]["data"]["payload"]["artifacts"] == [
        "commit_metadata.json"
    ]


@pytest.mark.asyncio
async def test_parse_artifacts_caches_evidence_summary_when_test_results_missing():
    commit_buf = io.BytesIO()
    with ZipFile(commit_buf, "w") as zf:
        zf.writestr(
            "commit_metadata.json",
            json.dumps(
                {
                    "schema_version": "1",
                    "repository_full_name": "org/repo",
                    "commit_sha": "abc123",
                    "workflow_run_id": "12",
                    "generated_at": "2026-03-13T00:00:00Z",
                    "status": "success",
                    "payload": {
                        "generatedAt": "2026-03-13T00:00:00Z",
                        "commits": [],
                    },
                }
            ),
        )

    client = StubClient(
        artifacts=[{"id": 2, "name": "winoe-commit-metadata"}],
        contents={2: commit_buf.getvalue()},
    )
    runner = GithubActionsRunner(client, workflow_file="winoe-evidence-capture.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 12)

    assert parsed is None
    assert error == "artifact_missing"
    cached_summary = runner._evidence_summary_cache[("org/repo", 12)]
    assert cached_summary["evidenceArtifacts"]["commitMetadata"]["artifactId"] == 2


@pytest.mark.asyncio
async def test_parse_artifacts_skips_expired():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("winoe-test-results.json", '{"passed":2,"failed":0,"total":2}')
    client = StubClient(
        artifacts=[{"id": 1, "name": "winoe-test-results", "expired": True}],
        contents={1: buf.getvalue()},
    )
    runner = GithubActionsRunner(client, workflow_file="winoe-evidence-capture.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 10)
    assert parsed is None
    assert error == "artifact_missing"


@pytest.mark.asyncio
async def test_parse_artifacts_handles_bad_zip_without_crashing():
    client = StubClient(
        artifacts=[{"id": 1, "name": "winoe-test-results"}],
        contents={1: b"this-is-not-a-zip"},
    )
    runner = GithubActionsRunner(client, workflow_file="winoe-evidence-capture.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 42)
    assert parsed is None
    assert error == "artifact_corrupt"


@pytest.mark.asyncio
async def test_parse_artifact_helpers_cover_download_failure_and_expired_filters():
    class FailureClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")

        async def download_artifact_zip(self, repo_full_name: str, artifact_id: int):
            raise GithubError(f"download failed for {repo_full_name}:{artifact_id}")

    runner = GithubActionsRunner(
        GithubClient(base_url="https://api.github.com", token="x"),
        workflow_file="winoe-evidence-capture.yml",
    )
    artifacts = [
        {"id": 1, "name": "winoe-test-results", "expired": True},
        {"id": 2, "name": "winoe-test-results"},
    ]

    assert _pick_test_artifacts(artifacts) == [{"id": 2, "name": "winoe-test-results"}]

    parsed, error, evidence = await _parse_first_test_artifact(
        FailureClient(),
        runner.cache,
        "org/repo",
        99,
        [{"id": 7, "name": "winoe-test-results"}],
    )
    assert parsed is None
    assert error == "artifact_download_failed"
    assert evidence == {}

    class EvidenceClient(GithubClient):
        def __init__(self):
            super().__init__(base_url="https://api.github.com", token="x")

        async def download_artifact_zip(self, repo_full_name: str, artifact_id: int):
            if artifact_id == 2:
                raise GithubError("boom")
            return b"not-a-zip"

    evidence = await _collect_evidence_artifacts(
        EvidenceClient(),
        "org/repo",
        [
            {"id": 2, "name": "winoe-commit-metadata"},
            {"id": 3, "name": "winoe-file-creation-timeline"},
        ],
    )
    assert evidence["commitMetadata"]["error"] == "artifact_download_failed"
    assert evidence["fileCreationTimeline"]["error"] == "artifact_corrupt"
