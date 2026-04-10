import pytest

from app.config import settings
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    TEMPLATE_CATALOG,
)
from tests.talent_partners.routes.talent_partners_admin_templates_health_utils import (
    MissingWorkflowGithubClient,
)


@pytest.mark.asyncio
async def test_admin_template_health_ok(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    resp = await async_client.get(
        "/api/admin/templates/health",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert len(payload["templates"]) == len(TEMPLATE_CATALOG)
    assert all(item["ok"] is True for item in payload["templates"])


@pytest.mark.asyncio
async def test_admin_template_health_missing_workflow(
    async_client, monkeypatch, override_dependencies
):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    with override_dependencies(
        {get_github_client: lambda: MissingWorkflowGithubClient()}
    ):
        resp = await async_client.get(
            "/api/admin/templates/health",
            headers={"X-Admin-Key": "test-admin-key"},
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is False
    assert payload["templates"] and payload["templates"][0]["ok"] is False
    assert "workflow_file_missing" in payload["templates"][0]["errors"]


@pytest.mark.asyncio
async def test_admin_template_health_missing_key(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    resp = await async_client.get("/api/admin/templates/health")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_template_health_wrong_key(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    resp = await async_client.get(
        "/api/admin/templates/health", headers={"X-Admin-Key": "wrong"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_template_health_live_mode_rejected(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    resp = await async_client.get(
        "/api/admin/templates/health?mode=live",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 400
