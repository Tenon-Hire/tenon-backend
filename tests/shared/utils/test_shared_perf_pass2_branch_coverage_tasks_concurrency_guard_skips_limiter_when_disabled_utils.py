from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_tasks_concurrency_guard_skips_limiter_when_disabled(monkeypatch):
    class _Limiter:
        def concurrency_guard(self, *_args, **_kwargs):
            raise AssertionError("limiter should not be called when disabled")

    monkeypatch.setattr(task_helpers.rate_limit, "rate_limit_enabled", lambda: False)
    monkeypatch.setattr(task_helpers.rate_limit, "limiter", _Limiter())

    async with task_helpers._concurrency_guard("session:1", 1):
        pass
