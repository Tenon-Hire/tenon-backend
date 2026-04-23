from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_composer_service import (
    build_ready_payload,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_build_ready_payload_uses_persisted_run_shape(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fit-composer@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
    )

    run = await evaluation_repo.create_run_with_day_scores(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 3, 12, 12, 3, tzinfo=UTC),
        generated_at=datetime(2026, 3, 12, 12, 3, tzinfo=UTC),
        model_name="fit-evaluator",
        model_version="2026-03-12",
        prompt_version="winoe-report-v1",
        rubric_version="rubric-v3",
        day2_checkpoint_sha="day2-cutoff",
        day3_final_sha="day3-cutoff",
        cutoff_commit_sha="day3-cutoff",
        transcript_reference="transcript:11",
        overall_winoe_score=0.78,
        recommendation="hire",
        confidence=0.82,
        metadata_json={"disabledDayIndexes": [4]},
        raw_report_json={"overallWinoeScore": 0.78},
        day_scores=[
            {
                "day_index": 2,
                "score": 0.75,
                "rubric_results_json": {"quality": 0.75},
                "evidence_pointers_json": [
                    {
                        "kind": "commit",
                        "ref": "abc123",
                        "url": "https://github.com/acme/repo/commit/abc123",
                    }
                ],
            },
            {
                "day_index": 4,
                "score": 0.9,
                "rubric_results_json": {"communication": 0.9},
                "evidence_pointers_json": [
                    {
                        "kind": "transcript",
                        "ref": "transcript:11",
                        "startMs": 10,
                        "endMs": 100,
                        "excerpt": "handoff explanation",
                    }
                ],
            },
        ],
    )

    payload = build_ready_payload(run)
    assert payload["status"] == "ready"
    assert payload["generatedAt"] == datetime(2026, 3, 12, 12, 3, tzinfo=UTC)

    report = payload["report"]
    assert report["overallWinoeScore"] == 0.78
    assert report["recommendation"] == "positive_signal"
    assert report["confidence"] == 0.82
    assert report["version"]["model"] == "fit-evaluator"
    assert report["version"]["promptVersion"] == "winoe-report-v1"
    assert report["version"]["rubricVersion"] == "rubric-v3"
    assert report["disabledDayIndexes"] == [4]

    transcript_evidence = report["dayScores"][1]["evidence"][0]
    assert transcript_evidence["kind"] == "transcript"
    assert transcript_evidence["startMs"] == 10
    assert transcript_evidence["endMs"] == 100
