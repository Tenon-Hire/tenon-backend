from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_FAILED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.evaluations.services import winoe_report_api
from tests.evaluations.services.evaluations_winoe_report_api_utils import build_context


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("run_status", "error_code", "expected"),
    [
        (EVALUATION_RUN_STATUS_PENDING, None, {"status": "running"}),
        (EVALUATION_RUN_STATUS_RUNNING, None, {"status": "running"}),
        (
            EVALUATION_RUN_STATUS_FAILED,
            None,
            {"status": "failed", "errorCode": "evaluation_failed"},
        ),
        (
            EVALUATION_RUN_STATUS_FAILED,
            "model_timeout",
            {"status": "failed", "errorCode": "model_timeout"},
        ),
        ("unexpected", None, {"status": "not_started"}),
    ],
)
async def test_fetch_winoe_report_latest_run_status_mapping(
    monkeypatch, run_status, error_code, expected
):
    context = build_context(candidate_session_id=42, company_id=88)
    latest_run = SimpleNamespace(status=run_status, error_code=error_code)
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
        AsyncMock(return_value=latest_run),
    )
    response = await winoe_report_api.fetch_winoe_report(
        object(), candidate_session_id=42, user=SimpleNamespace(id=1)
    )
    assert response == expected
