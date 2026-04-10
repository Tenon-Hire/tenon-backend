from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.evaluations.services import winoe_report_api
from tests.evaluations.services.evaluations_winoe_report_api_utils import build_context


@pytest.mark.asyncio
async def test_generate_winoe_report_queues_job(monkeypatch):
    context = build_context(candidate_session_id=77, company_id=88)

    async def _require(_db, *, candidate_session_id, user):
        assert candidate_session_id == 77
        assert user.id == 44
        return context

    enqueue = AsyncMock(return_value=SimpleNamespace(id="job-77"))
    monkeypatch.setattr(
        winoe_report_api, "require_talent_partner_candidate_session_context", _require
    )
    monkeypatch.setattr(winoe_report_api, "enqueue_evaluation_run", enqueue)
    response = await winoe_report_api.generate_winoe_report(
        object(), candidate_session_id=77, user=SimpleNamespace(id=44)
    )
    assert response == {"jobId": "job-77", "status": "queued"}
    enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_winoe_report_ready_uses_latest_success(monkeypatch):
    context = build_context(candidate_session_id=55, company_id=88)
    run = SimpleNamespace(id=1)
    monkeypatch.setattr(
        winoe_report_api,
        "require_talent_partner_candidate_session_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_successful_run_for_candidate_session",
        AsyncMock(return_value=run),
    )
    monkeypatch.setattr(
        winoe_report_api,
        "build_ready_payload",
        lambda value: {"status": "ready", "reportRunId": value.id},
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_run_for_candidate_session",
        AsyncMock(side_effect=AssertionError("should not be called")),
    )
    response = await winoe_report_api.fetch_winoe_report(
        object(), candidate_session_id=55, user=SimpleNamespace(id=1)
    )
    assert response == {"status": "ready", "reportRunId": 1}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("has_active_job", "expected"),
    [(True, {"status": "running"}), (False, {"status": "not_started"})],
)
async def test_fetch_winoe_report_when_no_runs(monkeypatch, has_active_job, expected):
    context = build_context(candidate_session_id=31, company_id=88)
    monkeypatch.setattr(
        winoe_report_api,
        "require_talent_partner_candidate_session_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_successful_run_for_candidate_session",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        winoe_report_api.evaluation_repo,
        "get_latest_run_for_candidate_session",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        winoe_report_api,
        "_has_active_evaluation_job",
        AsyncMock(return_value=has_active_job),
    )
    response = await winoe_report_api.fetch_winoe_report(
        object(), candidate_session_id=31, user=SimpleNamespace(id=1)
    )
    assert response == expected
