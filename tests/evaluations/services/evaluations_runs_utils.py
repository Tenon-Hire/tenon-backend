from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

from app.evaluations.repositories import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.evaluations.repositories import (
    repository as eval_repo,
)
from app.evaluations.services import (
    evaluations_services_evaluations_runs_service as eval_service,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


async def _seed_candidate_session(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="eval-service@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
    )
    await async_session.commit()
    return candidate_session


def _day_scores_payload() -> list[dict]:
    return [
        {
            "day_index": 2,
            "score": 84.5,
            "rubric_results_json": {"decision_quality": 4},
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
            "score": 90.0,
            "rubric_results_json": {"handoff_clarity": 5},
            "evidence_pointers_json": [
                {
                    "kind": "transcript",
                    "ref": "transcript:day4",
                    "startMs": 1200,
                    "endMs": 3400,
                }
            ],
        },
    ]


__all__ = [name for name in globals() if not name.startswith("__")]
