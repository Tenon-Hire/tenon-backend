from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_repo_state_service as repo_state_service,
)


class _FakeDB:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.flush_calls = 0
        self.refresh_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def flush(self) -> None:
        self.flush_calls += 1

    async def refresh(self, _model) -> None:
        self.refresh_calls += 1


@pytest.mark.asyncio
async def test_refresh_codespace_state_persists_github_state_change():
    db = _FakeDB()
    workspace = SimpleNamespace(
        repo_full_name="winoe-ai-repos/winoe-ws-123",
        codespace_name="codespace-123",
        codespace_state="Provisioning",
    )

    class StubGithubClient:
        async def get_codespace(self, repo_full_name: str, codespace_name: str):
            assert repo_full_name == "winoe-ai-repos/winoe-ws-123"
            assert codespace_name == "codespace-123"
            return {
                "name": codespace_name,
                "state": "Available",
                "web_url": "https://codespace-123.github.dev",
            }

    refreshed = await repo_state_service.refresh_codespace_state(
        db,
        workspace=workspace,
        github_client=StubGithubClient(),
    )

    assert refreshed is workspace
    assert workspace.codespace_state == "available"
    assert db.commit_calls == 1
    assert db.flush_calls == 0
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_refresh_codespace_state_noop_without_codespace_reader():
    db = _FakeDB()
    workspace = SimpleNamespace(
        repo_full_name="winoe-ai-repos/winoe-ws-123",
        codespace_name="codespace-123",
        codespace_state="Provisioning",
    )

    refreshed = await repo_state_service.refresh_codespace_state(
        db,
        workspace=workspace,
        github_client=object(),
    )

    assert refreshed is workspace
    assert workspace.codespace_state == "Provisioning"
    assert db.commit_calls == 0
    assert db.flush_calls == 0
    assert db.refresh_calls == 0
