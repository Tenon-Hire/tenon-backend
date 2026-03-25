from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.shared.auth.principal import Principal
from app.shared.http.routes import fit_profile as fit_profile_router
from app.shared.http.routes import shared_http_routes_jobs_routes as jobs_router
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_SUCCEEDED,
)
from app.shared.utils.shared_utils_errors_utils import ApiError


@pytest.mark.asyncio
async def test_fit_profile_router_generate_and_get_routes(monkeypatch):
    user = SimpleNamespace(id=7)
    monkeypatch.setattr(fit_profile_router, "ensure_recruiter", lambda _user: None)
    monkeypatch.setattr(
        fit_profile_router.fit_profile_api,
        "generate_fit_profile",
        AsyncMock(return_value={"jobId": "job-1", "status": "queued"}),
    )
    monkeypatch.setattr(
        fit_profile_router.fit_profile_api,
        "fetch_fit_profile",
        AsyncMock(return_value={"status": "running"}),
    )

    generated = await fit_profile_router.generate_fit_profile_route(11, object(), user)
    fetched = await fit_profile_router.get_fit_profile_route(11, object(), user)

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
        email="recruiter@test.com",
        name="Recruiter",
        roles=["recruiter"],
        permissions=["recruiter:access"],
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
        email="recruiter2@test.com",
        name="Recruiter 2",
        roles=["recruiter"],
        permissions=["recruiter:access"],
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
