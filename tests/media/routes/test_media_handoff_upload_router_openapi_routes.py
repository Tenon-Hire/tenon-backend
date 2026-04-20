from __future__ import annotations

from app.main import app


def test_handoff_upload_openapi_uses_canonical_handoff_routes(async_client):
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/tasks/{task_id}/handoff/upload/init" in paths
    assert "/api/tasks/{task_id}/handoff/upload/complete" in paths
    assert "/api/tasks/{task_id}/handoff/status" in paths
    assert "/api/tasks/{task_id}/presentation/upload/init" not in paths
    assert "/api/tasks/{task_id}/presentation/upload/complete" not in paths
    assert "/api/tasks/{task_id}/presentation/upload/status" not in paths
