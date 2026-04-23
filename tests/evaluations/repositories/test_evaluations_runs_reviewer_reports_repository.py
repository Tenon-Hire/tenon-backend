from __future__ import annotations

import pytest

from app.evaluations.repositories import repository as eval_repo
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_evidence_repository import (
    EvidencePointerValidationError,
)
from tests.evaluations.repositories.evaluations_runs_repository_utils import *


@pytest.mark.asyncio
async def test_add_reviewer_reports_is_idempotent_and_queryable(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    run = await eval_repo.create_run(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v5",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:reviewer",
        status=EVALUATION_RUN_STATUS_RUNNING,
    )

    payload = [
        {
            "day_index": 2,
            "reviewer_agent_key": "codeImplementationReviewer",
            "submission_kind": "code",
            "score": 0.81,
            "dimensional_scores_json": {"quality": 0.81},
            "evidence_citations_json": [
                {
                    "kind": "commit",
                    "ref": "abc123",
                    "url": "https://github.com/acme/repo/commit/abc123",
                    "dayIndex": 2,
                }
            ],
            "assessment_text": "Structured reviewer evidence.",
            "strengths_json": ["clear execution"],
            "risks_json": ["small coverage gap"],
            "raw_output_json": {"dayIndex": 2, "score": 0.81},
        },
        {
            "day_index": 3,
            "reviewer_agent_key": "codeImplementationReviewer",
            "submission_kind": "code",
            "score": 0.79,
            "dimensional_scores_json": {"quality": 0.79},
            "evidence_citations_json": [
                {
                    "kind": "test",
                    "ref": "workflow:ci",
                    "url": "https://github.com/acme/repo/actions/runs/42",
                    "dayIndex": 3,
                }
            ],
            "assessment_text": "Still aligned with the shared implementation rubric.",
            "strengths_json": ["consistent structure"],
            "risks_json": ["could broaden verification"],
            "raw_output_json": {"dayIndex": 3, "score": 0.79},
        },
    ]

    first = await eval_repo.add_reviewer_reports(
        async_session, run=run, reviewer_reports=payload, commit=True
    )
    second = await eval_repo.add_reviewer_reports(
        async_session, run=run, reviewer_reports=payload, commit=True
    )

    assert len(first) == 2
    assert len(second) == 2
    assert [row.id for row in first] == [row.id for row in second]

    by_run = await eval_repo.list_reviewer_reports_for_run(async_session, run_id=run.id)
    assert len(by_run) == 2
    assert [row.day_index for row in by_run] == [2, 3]
    assert [row.reviewer_agent_key for row in by_run] == [
        "codeImplementationReviewer",
        "codeImplementationReviewer",
    ]
    assert by_run[0].evidence_citations_json[0]["kind"] == "commit"
    assert by_run[1].evidence_citations_json[0]["kind"] == "tests"

    by_session = await eval_repo.list_reviewer_reports(
        async_session,
        candidate_session_id=candidate_session.id,
        reviewer_agent_key="codeImplementationReviewer",
        day_index=3,
        submission_kind="code",
    )
    assert len(by_session) == 1
    assert by_session[0].assessment_text == (
        "Still aligned with the shared implementation rubric."
    )


@pytest.mark.asyncio
async def test_add_reviewer_reports_rejects_unvalidated_evidence(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    run = await eval_repo.create_run(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-12",
        prompt_version="prompt.v5",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:reviewer",
        status=EVALUATION_RUN_STATUS_RUNNING,
    )

    with pytest.raises(EvidencePointerValidationError, match="evidence_pointers_json"):
        await eval_repo.add_reviewer_reports(
            async_session,
            run=run,
            reviewer_reports=[
                {
                    "day_index": 2,
                    "reviewer_agent_key": "codeImplementationReviewer",
                    "submission_kind": "code",
                    "score": 0.81,
                    "dimensional_scores_json": {"quality": 0.81},
                    "evidence_citations_json": [
                        {
                            "kind": "commit",
                            "url": "https://github.com/acme/repo/commit/abc123",
                        }
                    ],
                    "assessment_text": "Missing evidence ref should fail.",
                    "strengths_json": ["clear execution"],
                    "risks_json": ["small coverage gap"],
                    "raw_output_json": {"dayIndex": 2, "score": 0.81},
                }
            ],
            commit=False,
        )
