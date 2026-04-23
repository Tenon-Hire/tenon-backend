from __future__ import annotations

import pytest

from tests.evaluations.routes.evaluations_winoe_report_api_utils import *


@pytest.mark.asyncio
async def test_winoe_report_worker_completion_returns_ready_and_evidence(
    async_client,
    async_session,
    auth_header_factory,
):
    talent_partner, candidate_session = await _seed_completed_candidate_session(
        async_session
    )

    generate = await async_client.post(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report/generate",
        headers=auth_header_factory(talent_partner),
    )
    assert generate.status_code == 202, generate.text

    handled = await _run_worker_once(
        async_session, worker_id="winoe-report-worker-ready"
    )
    assert handled is True

    fetch = await async_client.get(
        f"/api/candidate_sessions/{candidate_session.id}/winoe_report",
        headers=auth_header_factory(talent_partner),
    )
    assert fetch.status_code == 200, fetch.text
    payload = fetch.json()
    assert payload["status"] == "ready"
    assert payload["generatedAt"] is not None
    report = payload["report"]
    assert isinstance(report["overallWinoeScore"], float)
    assert report["recommendation"] in {
        "strong_signal",
        "positive_signal",
        "mixed_signal",
        "limited_signal",
    }
    assert isinstance(report["confidence"], float)
    assert isinstance(report["dayScores"], list)
    assert isinstance(report["version"], dict)

    evidence_items = [
        evidence for day in report["dayScores"] for evidence in day.get("evidence", [])
    ]
    kinds = {item.get("kind") for item in evidence_items}
    assert "commit" in kinds
    assert "diff" in kinds
    assert "tests" in kinds
    assert "transcript" in kinds
    assert "submission" in kinds

    for item in evidence_items:
        if item.get("kind") == "transcript":
            assert isinstance(item.get("startMs"), int)
            assert isinstance(item.get("endMs"), int)
            assert item["endMs"] >= item["startMs"]
        if item.get("kind") == "commit":
            assert isinstance(item.get("ref"), str)
            assert item.get("url", "").startswith("https://")

    runs = await evaluation_repo.list_runs_for_candidate_session(
        async_session,
        candidate_session_id=candidate_session.id,
    )
    assert len(runs) == 1
    run = runs[0]
    assert run.status == EVALUATION_RUN_STATUS_COMPLETED
    assert run.basis_fingerprint is not None
    assert run.generated_at is not None
    assert run.job_id is not None
    assert run.day2_checkpoint_sha == "cutoff-day2-fixed"
    assert run.day3_final_sha == "cutoff-day3-fixed"

    marker = (
        await async_session.execute(
            select(WinoeReport).where(
                WinoeReport.candidate_session_id == candidate_session.id
            )
        )
    ).scalar_one_or_none()
    assert marker is not None
    assert marker.generated_at is not None
