from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.github.template_health import (
    integrations_github_template_health_github_template_health_live_dispatch_service as live_dispatch,
)
from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import (
    UTC,
    WorkflowRun,
    _LiveStubClient,
    datetime,
)


@pytest.mark.asyncio
async def test_live_dispatch_waits_when_run_not_finished(monkeypatch):
    sleep_calls: list[float] = []
    monotonic_values = iter([0.0, 0.0, 2.0])
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    in_progress_run = WorkflowRun(
        id=99,
        status="in_progress",
        conclusion=None,
        html_url="",
        head_sha="",
        event="workflow_dispatch",
        created_at=now_iso,
    )

    async def _fake_sleep(seconds: float):
        sleep_calls.append(seconds)

    def _monotonic():
        return next(monotonic_values, 2.0)

    monkeypatch.setattr(live_dispatch, "time", SimpleNamespace(monotonic=_monotonic))
    monkeypatch.setattr(live_dispatch.asyncio, "sleep", _fake_sleep)

    errors, run_id, conclusion = await live_dispatch.dispatch_and_poll(
        _LiveStubClient({"runs": [in_progress_run]}),
        repo_full_name="org/repo",
        workflow_file="ci.yml",
        default_branch="main",
        timeout_seconds=1,
    )

    assert errors == ["workflow_run_timeout"]
    assert run_id is None
    assert conclusion is None
    assert sleep_calls == [2.0]
