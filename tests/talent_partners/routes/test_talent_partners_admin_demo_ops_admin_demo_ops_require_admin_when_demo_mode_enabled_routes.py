from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_admin_demo_ops_require_admin_when_demo_mode_enabled(
    async_client, monkeypatch
):
    _enable_demo_mode(monkeypatch, allowlist_emails=[])
    response = await async_client.post(
        "/api/admin/jobs/job-123/requeue",
        json={"reason": "requeue for demo", "force": False},
        headers=_admin_headers("not-allowlisted@test.com"),
    )
    assert response.status_code == 403
