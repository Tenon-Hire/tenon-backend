from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.trials.services import (
    trials_services_trials_candidates_compare_summary_service as compare_summary_service,
)
from tests.trials.services.trials_candidates_compare_service_utils import *


def test_list_candidates_compare_summary_applies_order_display_and_updated_at_precedence(
    monkeypatch,
):
    access = SimpleNamespace(trial_id=42)
    report_time = datetime(2026, 3, 16, 10, 30, tzinfo=UTC)
    session_time = datetime(2026, 3, 16, 9, 15, tzinfo=UTC)
    rows = [
        _candidate_row(
            candidate_session_id=11,
            candidate_name="   ",
            candidate_session_status="completed",
            candidate_session_updated_at=session_time,
            winoe_report_generated_at=report_time,
            latest_success_candidate_session_id=11,
            latest_success_generated_at=report_time,
            latest_run_status="completed",
            overall_winoe_score=0.83,
            recommendation="mixed_signal",
        ),
        _candidate_row(
            candidate_session_id=7,
            candidate_name="Zed",
            candidate_session_status="completed",
            candidate_session_updated_at=session_time - timedelta(minutes=5),
            latest_success_candidate_session_id=7,
            latest_run_status="completed",
            overall_winoe_score=0.67,
            recommendation="positive_signal",
        ),
    ]
    load_day_completion = AsyncMock(
        return_value=(
            {
                11: {
                    "1": True,
                    "2": False,
                    "3": False,
                    "4": False,
                    "5": False,
                },
                7: {
                    "1": True,
                    "2": True,
                    "3": True,
                    "4": True,
                    "5": True,
                },
            },
            {11: None, 7: session_time - timedelta(minutes=5)},
        )
    )

    fetch_rows = AsyncMock(return_value=rows)
    monkeypatch.setattr(
        compare_summary_service, "fetch_candidate_compare_rows", fetch_rows
    )

    payload = asyncio.run(
        compare_summary_service.list_candidates_compare_summary(
            SimpleNamespace(),
            trial_id=42,
            user=SimpleNamespace(id=100, company_id=5),
            require_access=AsyncMock(return_value=access),
            load_day_completion_for_sessions=load_day_completion,
        )
    )

    assert payload["trialId"] == 42
    assert payload["cohortSize"] == 2
    assert payload["state"] == "partial"
    assert payload["message"] == (
        "Limited comparison — only 2 candidates completed this Trial."
    )
    assert [row["candidateSessionId"] for row in payload["candidates"]] == [11, 7]
    assert payload["candidates"][0]["candidateName"] == "Candidate A"
    assert payload["candidates"][0]["candidateDisplayName"] == "Candidate A"
    assert payload["candidates"][0]["updatedAt"] == report_time
    assert payload["candidates"][0]["recommendation"] == "mixed_signal"
    assert payload["candidates"][1]["candidateName"] == "Zed"
    assert payload["candidates"][1]["candidateDisplayName"] == "Zed"
    assert payload["candidates"][1]["updatedAt"] == session_time - timedelta(minutes=5)
    assert payload["candidates"][1]["recommendation"] == "positive_signal"
    fetch_rows.assert_awaited_once()
    assert load_day_completion.await_count == 1
