from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_admin_media_purge_route_is_covered(
    async_client,
    monkeypatch,
):
    admin_email = "ops-media-purge@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    response = await async_client.post(
        "/api/admin/media/purge",
        json={"batchLimit": 25},
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["scannedCount"] >= 0
    assert payload["purgedCount"] >= 0
    assert payload["failedCount"] >= 0
    assert isinstance(payload["purgedRecordingIds"], list)
