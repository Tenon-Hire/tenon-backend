from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_codespace_status_routes as status_routes,
)


@pytest.mark.asyncio
async def test_codespace_status_route_normalizes_naive_cutoff_at_to_utc(monkeypatch):
    workspace = SimpleNamespace(
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha=None,
        precommit_sha=None,
        latest_commit_sha=None,
        last_workflow_run_id=None,
        last_workflow_conclusion=None,
        id="ws-1",
    )
    task = SimpleNamespace(day_index=2)
    naive_cutoff = datetime(2026, 3, 10, 14, 30)

    async def _codespace_status(_db, *, candidate_session, task_id):
        assert candidate_session.id == 7
        assert task_id == 12
        return workspace, None, "https://codespaces.new/org/repo?quickstart=1", task

    async def _get_day_audit(_db, *, candidate_session_id, day_index):
        assert candidate_session_id == 7
        assert day_index == 2
        return SimpleNamespace(cutoff_commit_sha="abc123", cutoff_at=naive_cutoff)

    monkeypatch.setattr(status_routes, "codespace_status", _codespace_status)
    monkeypatch.setattr(status_routes.cs_repo, "get_day_audit", _get_day_audit)

    response = await status_routes.codespace_status_route(
        task_id=12,
        candidate_session=SimpleNamespace(id=7),
        db=object(),
    )

    assert response.cutoffCommitSha == "abc123"
    assert response.cutoffAt is not None
    assert response.cutoffAt.tzinfo == UTC
    assert response.cutoffAt == naive_cutoff.replace(tzinfo=UTC)
