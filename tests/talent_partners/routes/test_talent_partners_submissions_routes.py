from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.shared.http.routes import submissions as talent_partner_submissions


@pytest.mark.asyncio
async def test_list_submissions_handles_bad_json(monkeypatch):
    user = SimpleNamespace(id=8)
    sub = SimpleNamespace(
        id=11,
        candidate_session_id=22,
        task_id=5,
        submitted_at=datetime.now(UTC),
        code_repo_path=None,
        workflow_run_id=None,
        commit_sha=None,
        diff_summary_json="{not-json",
    )
    task = SimpleNamespace(day_index=2, type="design")
    cs = SimpleNamespace(id=33)
    sim = SimpleNamespace(id=44)

    monkeypatch.setattr(
        talent_partner_submissions, "ensure_talent_partner", lambda _u: None
    )

    async def _list_rows(*_a, **_k):
        return [(sub, task, cs, sim)]

    monkeypatch.setattr(
        talent_partner_submissions.talent_partner_sub_service,
        "list_submissions",
        _list_rows,
    )

    result = await talent_partner_submissions.list_submissions(
        db=None, user=user, candidateSessionId=None, taskId=None
    )
    assert result.items[0].diffSummary is None
    assert result.items[0].repoUrl is None


@pytest.mark.asyncio
async def test_talent_partner_list_builds_diff_url(monkeypatch):
    user = SimpleNamespace(id=10)
    sub = SimpleNamespace(
        id=33,
        candidate_session_id=44,
        task_id=5,
        submitted_at=datetime.now(UTC),
        code_repo_path="org/repo",
        workflow_run_id="99",
        commit_sha="sha",
        diff_summary_json=json.dumps({"base": "a", "head": "b"}),
    )
    task = SimpleNamespace(day_index=2, type="code")

    async def _list_rows(*_a, **_k):
        return [(sub, task, None, None)]

    monkeypatch.setattr(
        talent_partner_submissions, "ensure_talent_partner", lambda _u: None
    )
    monkeypatch.setattr(
        talent_partner_submissions.talent_partner_sub_service,
        "list_submissions",
        _list_rows,
    )

    result = await talent_partner_submissions.list_submissions(
        db=None, user=user, candidateSessionId=None, taskId=None
    )
    item = result.items[0]
    assert item.diffUrl.endswith("a...b")
    assert item.commitUrl.endswith("/commit/sha")
    assert item.workflowUrl.endswith("/runs/99")
