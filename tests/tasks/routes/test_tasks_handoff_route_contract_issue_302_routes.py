from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_handoff_routes_are_present_and_presentation_upload_routes_are_absent(
    async_client,
) -> None:
    response = await async_client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/tasks/{task_id}/handoff/upload/init" in paths
    assert "/api/tasks/{task_id}/handoff/upload/complete" in paths
    assert "/api/tasks/{task_id}/handoff/status" in paths
    assert all("presentation/upload" not in path for path in paths)


@pytest.mark.asyncio
async def test_legacy_presentation_upload_route_is_not_registered(async_client) -> None:
    response = await async_client.post("/api/tasks/123/presentation/upload/init")

    assert response.status_code == 404
