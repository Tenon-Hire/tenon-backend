from __future__ import annotations

import pytest

from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_rate_limiter_concurrency_guard_keeps_remaining_count():
    limiter = RateLimiter()
    limiter._in_flight["k"] = 1
    async with limiter.concurrency_guard("k", 2):
        assert limiter._in_flight["k"] == 2
    assert limiter._in_flight["k"] == 1
