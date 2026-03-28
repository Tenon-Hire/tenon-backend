from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_missing_headers_returns_401(async_client):
    resp = await async_client.post("/api/tasks/1/run", json={})
    assert resp.status_code == 401
    assert resp.json()["detail"] in {
        "Missing candidate session headers",
        "Not authenticated",
    }
