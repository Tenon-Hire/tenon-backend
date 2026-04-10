from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_admin_demo_ops_hidden_when_demo_mode_disabled(async_client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    response = await async_client.post(
        "/api/admin/jobs/job-123/requeue",
        json={"reason": "requeue for demo", "force": False},
        headers=_admin_headers(),
    )
    assert response.status_code == 404
