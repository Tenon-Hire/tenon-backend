from __future__ import annotations

import pytest

from tests.trials.routes.trials_create_api_utils import *


@pytest.mark.asyncio
async def test_create_trial_unauthorized_returns_401(async_client):
    payload = {
        "title": "Backend Node Trial",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "Build new API feature and debug an issue",
    }

    resp = await async_client.post("/api/trials", json=payload)
    assert resp.status_code == 401, resp.text
