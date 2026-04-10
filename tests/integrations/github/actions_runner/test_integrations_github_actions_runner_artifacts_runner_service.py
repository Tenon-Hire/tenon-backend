from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from zipfile import ZipFile

import pytest

from app.integrations.github.actions_runner import GithubActionsRunner
from app.integrations.github.client import GithubClient, WorkflowRun


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


def test_is_dispatched_run_filters_event_and_created_at():
    runner = GithubActionsRunner(DummyClient(), workflow_file="ci.yml")
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
    runner = GithubActionsRunner(client, workflow_file="ci.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 10)
    assert error is None
    assert parsed
    assert parsed.passed == 5
    assert parsed.failed == 1
    assert parsed.total == 6


@pytest.mark.asyncio
async def test_parse_artifacts_skips_expired():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("winoe-test-results.json", '{"passed":2,"failed":0,"total":2}')
    client = StubClient(
        artifacts=[{"id": 1, "name": "winoe-test-results", "expired": True}],
        contents={1: buf.getvalue()},
    )
    runner = GithubActionsRunner(client, workflow_file="ci.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 10)
    assert parsed is None
    assert error == "artifact_missing"


@pytest.mark.asyncio
async def test_parse_artifacts_handles_bad_zip_without_crashing():
    client = StubClient(
        artifacts=[{"id": 1, "name": "winoe-test-results"}],
        contents={1: b"this-is-not-a-zip"},
    )
    runner = GithubActionsRunner(client, workflow_file="ci.yml")
    parsed, error = await runner._parse_artifacts("org/repo", 42)
    assert parsed is None
    assert error == "artifact_corrupt"
