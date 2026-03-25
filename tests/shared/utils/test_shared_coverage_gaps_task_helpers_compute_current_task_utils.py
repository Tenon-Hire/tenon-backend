from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_task_helpers_compute_current_task(monkeypatch):
    current = object()

    async def _snapshot(*_a, **_k):
        return [], set(), current, 0, 1, False

    monkeypatch.setattr(task_helpers.cs_service, "progress_snapshot", _snapshot)
    assert await task_helpers._compute_current_task(object(), object()) is current
