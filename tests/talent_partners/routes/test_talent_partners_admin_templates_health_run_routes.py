import pytest

from app.config import settings
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    TEMPLATE_CATALOG,
)
from tests.talent_partners.routes.talent_partners_admin_templates_health_utils import (
    LiveGithubClient,
)


@pytest.mark.asyncio
async def test_admin_template_health_run_live(
    async_client, monkeypatch, override_dependencies
):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    template_key = next(iter(TEMPLATE_CATALOG))
    payload = {"templateKeys": [template_key], "mode": "live", "timeoutSeconds": 5}
    with override_dependencies({get_github_client: lambda: LiveGithubClient()}):
        resp = await async_client.post(
            "/api/admin/templates/health/run",
            json=payload,
            headers={"X-Admin-Key": "test-admin-key"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_admin_template_health_run_live_invalid_mode(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    template_key = next(iter(TEMPLATE_CATALOG))
    payload = {"templateKeys": [template_key], "mode": "static"}
    resp = await async_client.post(
        "/api/admin/templates/health/run",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_template_health_run_live_invalid_keys(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    payload = {"templateKeys": [], "mode": "live"}
    resp = await async_client.post(
        "/api/admin/templates/health/run",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_template_health_run_live_unknown_key(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    payload = {"templateKeys": ["does-not-exist"], "mode": "live"}
    resp = await async_client.post(
        "/api/admin/templates/health/run",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 422
    assert "Invalid templateKeys" in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_admin_template_health_run_rejects_too_many_keys(
    async_client, monkeypatch
):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    payload = {"templateKeys": ["a", "b", "c", "d", "e", "f"], "mode": "live"}
    resp = await async_client.post(
        "/api/admin/templates/health/run",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert resp.status_code == 422
