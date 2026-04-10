from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_pipeline_execute_service as execute_service,
)


@pytest.mark.asyncio
async def test_evaluate_and_finalize_run_enqueues_winoe_report_ready_notification(
    monkeypatch,
):
    db = SimpleNamespace(commit=AsyncMock())
    completed_run = SimpleNamespace(generated_at=datetime.now(UTC))
    complete_run = AsyncMock(return_value=completed_run)
    upsert_marker = AsyncMock()
    enqueue_notification = AsyncMock()

    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=SimpleNamespace(
                day_results=[
                    SimpleNamespace(
                        day_index=1,
                        score=0.8,
                        rubric_breakdown={"communication": 0.8},
                        evidence={"day": 1},
                    )
                ],
                overall_winoe_score=0.82,
                recommendation="hire",
                confidence=0.91,
                report_json={"summary": "ready"},
            )
        )
    )
    monkeypatch.setattr(
        execute_service.notification_service,
        "enqueue_winoe_report_ready_notification",
        enqueue_notification,
    )

    context = SimpleNamespace(candidate_session=SimpleNamespace(id=123, trial_id=456))

    result = await execute_service._evaluate_and_finalize_run(
        db=db,
        run=SimpleNamespace(id=7),
        evaluator=evaluator,
        bundle=SimpleNamespace(),
        evaluation_runs=SimpleNamespace(complete_run=complete_run),
        winoe_report_repository=SimpleNamespace(upsert_marker=upsert_marker),
        context=context,
        run_metadata={"source": "test"},
    )

    assert result is completed_run
    enqueue_notification.assert_awaited_once_with(
        db,
        candidate_session_id=123,
        trial_id=456,
        commit=False,
    )
    upsert_marker.assert_awaited_once()
    db.commit.assert_awaited_once()
