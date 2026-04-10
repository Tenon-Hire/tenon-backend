from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.shared.auth.principal import Principal
from app.shared.http.routes import shared_http_routes_jobs_routes as jobs_router
from app.shared.http.routes import winoe_report as winoe_report_router
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from app.shared.utils.shared_utils_errors_utils import ApiError


@pytest.mark.asyncio
async def test_winoe_report_router_generate_and_get_routes(monkeypatch):
    user = SimpleNamespace(id=7)
    monkeypatch.setattr(
        winoe_report_router, "ensure_talent_partner", lambda _user: None
    )
    monkeypatch.setattr(
        winoe_report_router.winoe_report_api,
        "generate_winoe_report",
        AsyncMock(return_value={"jobId": "job-1", "status": "queued"}),
    )
    monkeypatch.setattr(
        winoe_report_router.winoe_report_api,
        "fetch_winoe_report",
        AsyncMock(return_value={"status": "running"}),
    )

    generated = await winoe_report_router.generate_winoe_report_route(
        11, object(), user
    )
    fetched = await winoe_report_router.get_winoe_report_route(11, object(), user)

    assert generated.jobId == "job-1"
    assert generated.status == "queued"
    assert fetched.status == "running"


def test_jobs_router_public_status_and_poll_helpers():
    assert jobs_router._public_job_status(JOB_STATUS_SUCCEEDED) == "completed"
    assert jobs_router._public_job_status(JOB_STATUS_DEAD_LETTER) == "failed"
    assert jobs_router._public_job_status("queued") == "queued"

    assert jobs_router._poll_after_ms_for_status(JOB_STATUS_QUEUED) == 1500
    assert jobs_router._poll_after_ms_for_status(JOB_STATUS_SUCCEEDED) == 0


@pytest.mark.asyncio
async def test_jobs_router_get_job_status_not_found(monkeypatch):
    principal = Principal(
        sub="auth0|1",
        email="talent_partner@test.com",
        name="TalentPartner",
        roles=["talent_partner"],
        permissions=["talent_partner:access"],
        claims={},
    )
    monkeypatch.setattr(
        jobs_router.jobs_repo,
        "get_by_id_for_principal",
        AsyncMock(return_value=None),
    )

    with pytest.raises(ApiError) as exc:
        await jobs_router.get_job_status("job-missing", object(), principal)
    assert exc.value.status_code == 404
    assert exc.value.error_code == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_jobs_router_get_job_status_success(monkeypatch):
    principal = Principal(
        sub="auth0|2",
        email="talent_partner2@test.com",
        name="TalentPartner 2",
        roles=["talent_partner"],
        permissions=["talent_partner:access"],
        claims={},
    )
    job = SimpleNamespace(
        id="job-22",
        job_type="evaluation_run",
        status=JOB_STATUS_SUCCEEDED,
        attempt=1,
        max_attempts=5,
        result_json={"ok": True},
        last_error=None,
    )
    monkeypatch.setattr(
        jobs_router.jobs_repo,
        "get_by_id_for_principal",
        AsyncMock(return_value=job),
    )
    response = await jobs_router.get_job_status("job-22", object(), principal)

    assert response.jobId == "job-22"
    assert response.status == "completed"
    assert response.pollAfterMs == 0
    assert response.result == {"ok": True}
