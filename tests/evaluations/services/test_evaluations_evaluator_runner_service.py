from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import AIPolicySnapshotError, build_ai_policy_snapshot
from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATION_NO_HIRE,
)
from app.evaluations.services import evaluator
from tests.evaluations.services.evaluations_evaluator_branch_gap_utils import day_input


def _snapshot():
    simulation = SimpleNamespace(
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    return build_ai_policy_snapshot(simulation=simulation)


async def test_deterministic_evaluator_handles_empty_enabled_days():
    bundle = evaluator.EvaluationInputBundle(
        candidate_session_id=1,
        scenario_version_id=2,
        model_name="model-x",
        model_version="v1",
        prompt_version="p1",
        rubric_version="r1",
        disabled_day_indexes=[1],
        day_inputs=[day_input(day_index=1, content_text="text")],
        ai_policy_snapshot_json=_snapshot(),
    )
    result = await evaluator.DeterministicFitProfileEvaluator().evaluate(bundle)
    assert result.overall_fit_score == 0.0
    assert result.confidence == 0.0
    assert result.recommendation == EVALUATION_RECOMMENDATION_NO_HIRE
    assert result.day_results == []
    assert result.report_json["dayScores"] == [
        {
            "dayIndex": 1,
            "status": "human_review_required",
            "reason": "ai_eval_disabled_for_day",
        }
    ]


async def test_deterministic_evaluator_sorts_days_and_builds_report():
    bundle = evaluator.EvaluationInputBundle(
        candidate_session_id=10,
        scenario_version_id=20,
        model_name="model-y",
        model_version="v2",
        prompt_version="p2",
        rubric_version="r2",
        disabled_day_indexes=[],
        day_inputs=[
            day_input(day_index=5, content_text="final reflection"),
            day_input(
                day_index=2,
                repo_full_name="acme/repo",
                cutoff_commit_sha="cutoff-sha",
                diff_summary={"base": "a", "head": "b"},
                tests_passed=4,
                tests_failed=0,
                workflow_run_id="555",
            ),
        ],
        ai_policy_snapshot_json=_snapshot(),
    )
    result = await evaluator.get_fit_profile_evaluator().evaluate(bundle)
    assert [day.day_index for day in result.day_results] == [2, 5]
    assert 0 <= result.overall_fit_score <= 1
    assert 0 <= result.confidence <= 1
    assert result.report_json["version"]["modelVersion"] == "v2"
    assert result.report_json["dayScores"][0]["dayIndex"] == 2


async def test_live_evaluator_requires_snapshot():
    bundle = evaluator.EvaluationInputBundle(
        candidate_session_id=10,
        scenario_version_id=20,
        model_name="model-y",
        model_version="v2",
        prompt_version="p2",
        rubric_version="r2",
        disabled_day_indexes=[],
        day_inputs=[day_input(day_index=5, content_text="final reflection")],
    )
    with pytest.raises(
        AIPolicySnapshotError,
        match="scenario_version_ai_policy_snapshot_missing",
    ):
        await evaluator.get_fit_profile_evaluator().evaluate(bundle)


async def test_deterministic_evaluator_requires_snapshot():
    bundle = evaluator.EvaluationInputBundle(
        candidate_session_id=10,
        scenario_version_id=20,
        model_name="model-y",
        model_version="v2",
        prompt_version="p2",
        rubric_version="r2",
        disabled_day_indexes=[],
        day_inputs=[day_input(day_index=1, content_text="text")],
    )
    with pytest.raises(
        AIPolicySnapshotError,
        match="scenario_version_ai_policy_snapshot_missing",
    ):
        await evaluator.DeterministicFitProfileEvaluator().evaluate(bundle)
