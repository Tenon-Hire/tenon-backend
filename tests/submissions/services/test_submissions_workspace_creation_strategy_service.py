from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.services import workspace_creation_strategy as strategy


@pytest.mark.asyncio
async def test_resolve_workspace_strategy_prefers_explicit_resolution(monkeypatch):
    monkeypatch.setattr(
        strategy, "resolve_workspace_key_for_task", lambda _task: "base-key"
    )
    workspace_group = SimpleNamespace(id=99)
    workspace_resolution = SimpleNamespace(
        workspace_key="resolved-key",
        uses_grouped_workspace=True,
        workspace_group=workspace_group,
        workspace_group_checked=1,
    )

    result = await strategy.resolve_workspace_strategy(
        db=object(),
        candidate_session=SimpleNamespace(id=10),
        task=SimpleNamespace(id=20, day_index=3, type="code"),
        workspace_resolution=workspace_resolution,
    )

    assert result == ("resolved-key", True, workspace_group, True)


@pytest.mark.asyncio
async def test_resolve_workspace_strategy_uses_resolution_repo_when_db_can_execute(
    monkeypatch,
):
    monkeypatch.setattr(
        strategy, "resolve_workspace_key_for_task", lambda _task: "base-key"
    )
    called: dict[str, object] = {}

    async def _resolve_workspace_resolution(db, **kwargs):
        called["db"] = db
        called.update(kwargs)
        return SimpleNamespace(
            workspace_key=None,
            uses_grouped_workspace=False,
            workspace_group=None,
            workspace_group_checked=0,
        )

    monkeypatch.setattr(
        strategy.workspace_repo,
        "resolve_workspace_resolution",
        _resolve_workspace_resolution,
    )

    class _DB:
        async def execute(self, _stmt):
            return None

    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=21, day_index=4, type="code")
    db = _DB()

    result = await strategy.resolve_workspace_strategy(
        db=db,
        candidate_session=candidate_session,
        task=task,
        workspace_resolution=None,
    )

    assert result == ("base-key", False, None, False)
    assert called["db"] is db
    assert called["candidate_session_id"] == 11
    assert called["task_id"] == 21
    assert called["task_day_index"] == 4
    assert called["task_type"] == "code"


@pytest.mark.asyncio
async def test_resolve_workspace_strategy_fallback_group_lookup_suppresses_attribute_error(
    monkeypatch,
):
    monkeypatch.setattr(
        strategy, "resolve_workspace_key_for_task", lambda _task: "group-key"
    )

    async def _uses_grouped_workspace(*_args, **_kwargs):
        return True

    async def _get_workspace_group(*_args, **_kwargs):
        raise AttributeError("missing relationship")

    monkeypatch.setattr(
        strategy.workspace_repo,
        "session_uses_grouped_workspace",
        _uses_grouped_workspace,
    )
    monkeypatch.setattr(
        strategy.workspace_repo, "get_workspace_group", _get_workspace_group
    )

    result = await strategy.resolve_workspace_strategy(
        db=SimpleNamespace(),
        candidate_session=SimpleNamespace(id=12),
        task=SimpleNamespace(id=22, day_index=2, type="code"),
        workspace_resolution=None,
    )

    assert result == ("group-key", True, None, False)


@pytest.mark.asyncio
async def test_resolve_workspace_strategy_fallback_non_grouped_skips_group_lookup(
    monkeypatch,
):
    monkeypatch.setattr(
        strategy, "resolve_workspace_key_for_task", lambda _task: "solo-key"
    )
    calls = {"group_lookup": 0}

    async def _uses_grouped_workspace(*_args, **_kwargs):
        return False

    async def _get_workspace_group(*_args, **_kwargs):
        calls["group_lookup"] += 1
        return SimpleNamespace(id=1)

    monkeypatch.setattr(
        strategy.workspace_repo,
        "session_uses_grouped_workspace",
        _uses_grouped_workspace,
    )
    monkeypatch.setattr(
        strategy.workspace_repo, "get_workspace_group", _get_workspace_group
    )

    result = await strategy.resolve_workspace_strategy(
        db=SimpleNamespace(),
        candidate_session=SimpleNamespace(id=13),
        task=SimpleNamespace(id=23, day_index=5, type="text"),
        workspace_resolution=None,
    )

    assert result == ("solo-key", False, None, False)
    assert calls["group_lookup"] == 0
