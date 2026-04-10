from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.shared.jobs.handlers import (
    shared_jobs_handlers_evaluation_run_handler as evaluation_handler,
)
from app.shared.jobs.shared_jobs_worker_service import PermanentJobError


@pytest.mark.asyncio
async def test_handle_evaluation_run_returns_success_result(monkeypatch):
    process = AsyncMock(return_value={"status": "completed", "evaluationRunId": 1})
    monkeypatch.setattr(
        evaluation_handler.winoe_report_pipeline,
        "process_evaluation_run_job",
        process,
    )

    response = await evaluation_handler.handle_evaluation_run({"jobId": "job-1"})
    assert response == {"status": "completed", "evaluationRunId": 1}


@pytest.mark.asyncio
async def test_handle_evaluation_run_raises_permanent_error_for_failed_domain_result(
    monkeypatch,
):
    process = AsyncMock(
        return_value={"status": "failed", "errorCode": "evaluation_failed"}
    )
    monkeypatch.setattr(
        evaluation_handler.winoe_report_pipeline,
        "process_evaluation_run_job",
        process,
    )

    with pytest.raises(PermanentJobError, match="evaluation_run_failed"):
        await evaluation_handler.handle_evaluation_run({"jobId": "job-2"})
