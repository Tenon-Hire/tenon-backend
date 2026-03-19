"""
GAP-FILLING TESTS: candidate session + submissions service branch coverage

Gaps identified:
- app/services/candidate_sessions/{claims,fetch_owned,status,ownership,invites}.py
- app/services/submissions/{codespace_urls,rate_limits,task_rules,submission_progress}.py
- app/services/submissions/use_cases/{submit_task,codespace_init}.py

These tests supplement existing unit/integration coverage and target branch-only
misses that were not exercised by the main suite.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.services.candidate_sessions import claims as claims_service
from app.services.candidate_sessions import fetch_owned as fetch_owned_service
from app.services.candidate_sessions import invites as invites_service
from app.services.candidate_sessions import ownership as ownership_service
from app.services.candidate_sessions import status as status_service
from app.services.submissions import (
    codespace_urls,
    rate_limits,
    submission_progress,
    task_rules,
)
from app.services.submissions.use_cases import codespace_init as codespace_init_service
from app.services.submissions.use_cases import submit_task as submit_task_service


class _DummyDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0
        self.flushes = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        self.refreshes += 1

    async def flush(self):
        self.flushes += 1

    @asynccontextmanager
    async def begin_nested(self):
        yield


@pytest.mark.asyncio
async def test_claim_invite_with_principal_skips_commit_when_no_changes(monkeypatch):
    now = datetime.now(UTC)
    db = _DummyDB()
    candidate_session = SimpleNamespace(status="in_progress", started_at=now)

    async def _fake_fetch(_db, _token, *, now):
        return candidate_session

    monkeypatch.setattr(claims_service, "fetch_by_token_for_update", _fake_fetch)
    monkeypatch.setattr(
        claims_service, "ensure_candidate_ownership", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        claims_service, "mark_in_progress", lambda *_args, **_kwargs: None
    )

    loaded = await claims_service.claim_invite_with_principal(
        db,
        "token",
        SimpleNamespace(),
        now=now,
    )

    assert loaded is candidate_session
    assert db.commits == 0
    assert db.refreshes == 0


@pytest.mark.asyncio
async def test_fetch_owned_session_skips_commit_for_existing_claim_no_updates(
    monkeypatch,
):
    now = datetime.now(UTC)
    db = _DummyDB()
    candidate_session = SimpleNamespace(candidate_auth0_sub="auth0|already")

    async def _get_by_id(_db, _session_id):
        return candidate_session

    monkeypatch.setattr(fetch_owned_service.cs_repo, "get_by_id", _get_by_id)
    monkeypatch.setattr(
        fetch_owned_service, "ensure_can_access", lambda cs, *_args, **_kwargs: cs
    )
    monkeypatch.setattr(
        fetch_owned_service,
        "ensure_candidate_ownership",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        fetch_owned_service, "apply_auth_updates", lambda *_args, **_kwargs: False
    )

    loaded = await fetch_owned_service.fetch_owned_session(
        db,
        session_id=1,
        principal=SimpleNamespace(),
        now=now,
    )

    assert loaded is candidate_session
    assert db.commits == 0
    assert db.refreshes == 0


@pytest.mark.asyncio
async def test_fetch_owned_session_skips_commit_after_lock_when_no_updates(monkeypatch):
    now = datetime.now(UTC)
    db = _DummyDB()
    candidate_session = SimpleNamespace(candidate_auth0_sub=None)

    async def _get_by_id(_db, _session_id):
        return candidate_session

    async def _get_by_id_for_update(_db, _session_id):
        return candidate_session

    monkeypatch.setattr(fetch_owned_service.cs_repo, "get_by_id", _get_by_id)
    monkeypatch.setattr(
        fetch_owned_service.cs_repo, "get_by_id_for_update", _get_by_id_for_update
    )
    monkeypatch.setattr(
        fetch_owned_service, "ensure_can_access", lambda cs, *_args, **_kwargs: cs
    )
    monkeypatch.setattr(
        fetch_owned_service,
        "ensure_candidate_ownership",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        fetch_owned_service, "apply_auth_updates", lambda *_args, **_kwargs: False
    )

    loaded = await fetch_owned_service.fetch_owned_session(
        db,
        session_id=1,
        principal=SimpleNamespace(),
        now=now,
    )

    assert loaded is candidate_session
    assert db.commits == 0
    assert db.refreshes == 0


def test_mark_in_progress_preserves_existing_started_at():
    existing_started_at = datetime(2026, 1, 1, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        status="not_started", started_at=existing_started_at
    )

    status_service.mark_in_progress(candidate_session, now=datetime.now(UTC))

    assert candidate_session.status == "in_progress"
    assert candidate_session.started_at == existing_started_at


def test_ensure_candidate_ownership_does_not_overwrite_claimed_at_when_present():
    now = datetime.now(UTC)
    claimed_at = datetime(2025, 1, 1, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        invite_email="candidate@example.com",
        candidate_auth0_sub=None,
        candidate_auth0_email="candidate@example.com",
        candidate_email="candidate@example.com",
        claimed_at=claimed_at,
    )
    principal = SimpleNamespace(
        email="candidate@example.com",
        sub="auth0|candidate",
        claims={"email_verified": True},
    )

    changed = ownership_service.ensure_candidate_ownership(
        candidate_session,
        principal,
        now=now,
    )

    assert changed is True
    assert candidate_session.candidate_auth0_sub == "auth0|candidate"
    assert candidate_session.claimed_at == claimed_at


@pytest.mark.asyncio
async def test_invite_list_reuses_cached_tasks_per_simulation(monkeypatch):
    sessions = [
        SimpleNamespace(id=1, simulation_id=22),
        SimpleNamespace(id=2, simulation_id=22),
    ]
    principal = SimpleNamespace(email="candidate@example.com")
    calls = {"tasks_for_simulation": 0}

    async def _list_for_email(_db, _email, include_terminated=False):
        assert include_terminated is False
        return sessions

    async def _last_submission_map(_db, session_ids):
        assert session_ids == [1, 2]
        return {}

    async def _tasks_for_simulation(_db, simulation_id):
        calls["tasks_for_simulation"] += 1
        assert simulation_id == 22
        return [SimpleNamespace(id=101)]

    async def _build_invite_item(
        _db,
        cs,
        *,
        now,
        last_submitted_map,
        tasks_loader,
    ):
        assert isinstance(now, datetime)
        assert last_submitted_map == {}
        tasks = await tasks_loader(cs.simulation_id)
        return {"sessionId": cs.id, "taskCount": len(tasks)}

    monkeypatch.setattr(invites_service.cs_repo, "list_for_email", _list_for_email)
    monkeypatch.setattr(
        invites_service.cs_repo, "tasks_for_simulation", _tasks_for_simulation
    )
    monkeypatch.setattr(invites_service, "last_submission_map", _last_submission_map)
    monkeypatch.setattr(invites_service, "build_invite_item", _build_invite_item)

    items = await invites_service.invite_list_for_principal(
        _DummyDB(),
        principal,
    )

    assert len(items) == 2
    assert calls["tasks_for_simulation"] == 1


@pytest.mark.asyncio
async def test_ensure_canonical_workspace_url_updates_noncanonical_url():
    db = _DummyDB()
    workspace = SimpleNamespace(
        repo_full_name="acme/repo",
        codespace_url="https://example.com/old",
    )

    resolved = await codespace_urls.ensure_canonical_workspace_url(db, workspace)

    assert resolved.startswith("https://codespaces.new/acme/repo")
    assert workspace.codespace_url == resolved
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_ensure_canonical_workspace_url_noop_when_equal_but_not_marked_canonical(
    monkeypatch,
):
    db = _DummyDB()
    canonical = "https://codespaces.new/acme/repo?quickstart=1"
    workspace = SimpleNamespace(
        repo_full_name="acme/repo",
        codespace_url=canonical,
    )

    monkeypatch.setattr(
        codespace_urls, "is_canonical_codespace_url", lambda _url: False
    )

    resolved = await codespace_urls.ensure_canonical_workspace_url(db, workspace)

    assert resolved == canonical
    assert workspace.codespace_url == canonical
    assert db.commits == 0
    assert db.refreshes == 0


def test_rate_limit_rules_fallback_when_override_is_not_dict(monkeypatch):
    from app.api.routers import tasks_codespaces

    monkeypatch.setattr(tasks_codespaces, "_RATE_LIMIT_RULE", "invalid", raising=False)
    resolved = rate_limits._rules()
    assert resolved == rate_limits._DEFAULT_RATE_LIMIT_RULES


@pytest.mark.asyncio
async def test_ensure_not_duplicate_noop_when_repository_returns_none(monkeypatch):
    from app.domains.submissions import service_candidate as submission_service

    async def _no_duplicate(_db, _candidate_session_id, _task_id):
        return None

    monkeypatch.setattr(
        submission_service.submissions_repo,
        "find_duplicate",
        _no_duplicate,
    )

    await task_rules.ensure_not_duplicate(None, 10, 20)


@pytest.mark.asyncio
async def test_progress_after_submission_skips_commit_for_already_completed(
    monkeypatch,
):
    db = _DummyDB()
    candidate_session = SimpleNamespace(
        status="completed", completed_at=datetime.now(UTC)
    )

    async def _snapshot(_db, _candidate_session):
        return (
            None,
            {1, 2, 3, 4, 5},
            None,
            5,
            5,
            True,
        )

    monkeypatch.setattr(submission_progress.cs_service, "progress_snapshot", _snapshot)

    completed, total, is_complete = await submission_progress.progress_after_submission(
        db,
        candidate_session,
        now=datetime.now(UTC),
    )

    assert (completed, total, is_complete) == (5, 5, True)
    assert db.commits == 0
    assert db.refreshes == 0


@pytest.mark.asyncio
async def test_progress_after_submission_keeps_existing_completed_at(monkeypatch):
    db = _DummyDB()
    completed_at = datetime(2025, 1, 1, tzinfo=UTC)
    candidate_session = SimpleNamespace(status="in_progress", completed_at=completed_at)

    async def _snapshot(_db, _candidate_session):
        return (
            None,
            {1, 2, 3, 4, 5},
            None,
            5,
            5,
            True,
        )

    monkeypatch.setattr(submission_progress.cs_service, "progress_snapshot", _snapshot)

    completed, total, is_complete = await submission_progress.progress_after_submission(
        db,
        candidate_session,
        now=datetime.now(UTC),
    )

    assert (completed, total, is_complete) == (5, 5, True)
    assert candidate_session.status == "completed"
    assert candidate_session.completed_at == completed_at
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_submit_task_skips_code_submission_for_non_code_task(monkeypatch):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=12)
    task = SimpleNamespace(id=33, type="design")
    payload = SimpleNamespace(contentText="design text")
    created_submission = SimpleNamespace(id=501)

    calls = {"rate_limit": 0, "run_code_submission": 0}

    def _apply_rate_limit(_session_id, _action):
        calls["rate_limit"] += 1

    async def _validate(_db, _candidate_session, _task_id, _payload):
        return task, {"kind": "design"}

    async def _run_code_submission(**_kwargs):
        calls["run_code_submission"] += 1
        return "should-not-run"

    async def _create_submission(*_args, **_kwargs):
        return created_submission

    async def _progress_after_submission(*_args, **_kwargs):
        return (1, 5, False)

    monkeypatch.setattr(submit_task_service, "apply_rate_limit", _apply_rate_limit)
    monkeypatch.setattr(submit_task_service, "validate_submission_flow", _validate)
    monkeypatch.setattr(
        submit_task_service, "run_code_submission", _run_code_submission
    )
    monkeypatch.setattr(
        submit_task_service.submission_service,
        "is_code_task",
        lambda _task: False,
    )
    monkeypatch.setattr(
        submit_task_service.submission_service, "create_submission", _create_submission
    )
    monkeypatch.setattr(
        submit_task_service.submission_service,
        "progress_after_submission",
        _progress_after_submission,
    )

    (
        task_loaded,
        submission,
        completed,
        total,
        is_complete,
    ) = await submit_task_service.submit_task(
        db,
        candidate_session=candidate_session,
        task_id=33,
        payload=payload,
        github_client=SimpleNamespace(),
        actions_runner=SimpleNamespace(),
    )

    assert task_loaded is task
    assert submission is created_submission
    assert (completed, total, is_complete) == (1, 5, False)
    assert calls["rate_limit"] == 1
    assert calls["run_code_submission"] == 0


@pytest.mark.asyncio
async def test_init_codespace_skips_username_commit_when_unchanged(monkeypatch):
    db = _DummyDB()
    candidate_session = SimpleNamespace(id=7, github_username="octocat")
    task = SimpleNamespace(id=99)
    workspace = SimpleNamespace(repo_full_name="acme/repo", codespace_url=None)

    def _apply_rate_limit(_session_id, _action):
        return None

    async def _validate_request(_db, _candidate_session, _task_id):
        return task

    async def _ensure_workspace(_db, **_kwargs):
        return workspace

    async def _ensure_canonical(_db, _workspace):
        return "https://codespaces.new/acme/repo?quickstart=1"

    monkeypatch.setattr(codespace_init_service, "apply_rate_limit", _apply_rate_limit)
    monkeypatch.setattr(
        codespace_init_service, "validate_codespace_request", _validate_request
    )
    monkeypatch.setattr(
        codespace_init_service.submission_service, "ensure_workspace", _ensure_workspace
    )
    monkeypatch.setattr(
        codespace_init_service,
        "ensure_canonical_workspace_url",
        _ensure_canonical,
    )
    monkeypatch.setattr(
        codespace_init_service.submission_service,
        "build_codespace_url",
        lambda repo_full_name: f"https://codespaces.new/{repo_full_name}",
    )

    (
        loaded_workspace,
        built_url,
        canonical_url,
        loaded_task,
    ) = await codespace_init_service.init_codespace(
        db,
        candidate_session=candidate_session,
        task_id=99,
        github_client=SimpleNamespace(),
        github_username="  octocat  ",
        repo_prefix="tenon-",
        template_owner=None,
        now=datetime.now(UTC),
    )

    assert loaded_workspace is workspace
    assert loaded_task is task
    assert built_url == "https://codespaces.new/acme/repo"
    assert canonical_url == "https://codespaces.new/acme/repo?quickstart=1"
    assert db.commits == 0
