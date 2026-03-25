from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_task_helpers_concurrency_guard_uses_rate_limiter(monkeypatch):
    calls = {"entered": 0, "exited": 0}

    @asynccontextmanager
    async def _fake_guard(_key, _limit):
        calls["entered"] += 1
        yield
        calls["exited"] += 1

    monkeypatch.setattr(task_helpers.rate_limit, "rate_limit_enabled", lambda: True)
    monkeypatch.setattr(
        task_helpers.rate_limit.limiter, "concurrency_guard", _fake_guard
    )
    async with task_helpers._concurrency_guard("k", 1):
        pass
    assert calls == {"entered": 1, "exited": 1}
