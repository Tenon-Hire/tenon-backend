from __future__ import annotations

from app.repositories.evaluations.models import (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
)
from app.services.evaluations import evaluator


def _day_input(
    *,
    day_index: int,
    content_text: str | None = None,
    content_json: dict | None = None,
    repo_full_name: str | None = None,
    commit_sha: str | None = None,
    workflow_run_id: str | None = None,
    diff_summary: dict | None = None,
    tests_passed: int | None = None,
    tests_failed: int | None = None,
    transcript_reference: str | None = None,
    transcript_segments: list[dict] | None = None,
    cutoff_commit_sha: str | None = None,
) -> evaluator.DayEvaluationInput:
    return evaluator.DayEvaluationInput(
        day_index=day_index,
        task_id=day_index,
        task_type=f"day_{day_index}",
        submission_id=100 + day_index,
        content_text=content_text,
        content_json=content_json,
        repo_full_name=repo_full_name,
        commit_sha=commit_sha,
        workflow_run_id=workflow_run_id,
        diff_summary=diff_summary,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        transcript_reference=transcript_reference,
        transcript_segments=transcript_segments or [],
        cutoff_commit_sha=cutoff_commit_sha,
        eval_basis_ref=None,
    )


def test_evaluator_helper_functions():
    assert evaluator._safe_repo_full_name(None) is None
    assert evaluator._safe_repo_full_name("bad repo name") is None
    assert evaluator._safe_repo_full_name(" acme/repo-1 ") == "acme/repo-1"

    assert evaluator._to_excerpt(None) is None
    assert evaluator._to_excerpt("   \n  ") is None
    assert evaluator._to_excerpt("hello\nworld") == "hello world"
    assert evaluator._to_excerpt("x" * 20, max_chars=5) == "xxxxx"

    assert evaluator._safe_int(True) is None
    assert evaluator._safe_int(7) == 7
    assert evaluator._safe_int(7.9) == 7
    assert evaluator._safe_int("7") is None

    assert evaluator._segment_start_ms({"startMs": 10}) == 10
    assert evaluator._segment_start_ms({"start_ms": -2}) == 0
    assert evaluator._segment_start_ms({"start": 3.5}) == 3
    assert evaluator._segment_start_ms({"unknown": 1}) is None
    assert evaluator._segment_end_ms({"endMs": 20}) == 20
    assert evaluator._segment_end_ms({"end_ms": -1}) == 0
    assert evaluator._segment_end_ms({"end": 4.9}) == 4
    assert evaluator._segment_end_ms({"unknown": 1}) is None
    assert evaluator._segment_text({"text": "hello"}) == "hello"
    assert evaluator._segment_text({"content": "world"}) == "world"
    assert evaluator._segment_text({"excerpt": "snippet"}) == "snippet"
    assert evaluator._segment_text({"text": "  "}) is None


def test_recommendation_thresholds():
    assert (
        evaluator._recommendation_from_score(0.9)
        == EVALUATION_RECOMMENDATION_STRONG_HIRE
    )
    assert evaluator._recommendation_from_score(0.7) == EVALUATION_RECOMMENDATION_HIRE
    assert (
        evaluator._recommendation_from_score(0.55)
        == EVALUATION_RECOMMENDATION_LEAN_HIRE
    )
    assert (
        evaluator._recommendation_from_score(0.54) == EVALUATION_RECOMMENDATION_NO_HIRE
    )


def test_build_day_evidence_for_day2_day4_and_fallback():
    day2 = _day_input(
        day_index=2,
        repo_full_name="bad repo",
        commit_sha="head-sha",
        workflow_run_id="  ",
        diff_summary={"base": "a1", "head": "b2"},
        tests_passed=3,
        tests_failed=1,
        cutoff_commit_sha="cutoff-sha",
    )
    evidence_day2 = evaluator._build_day_evidence(day2)
    assert [item["kind"] for item in evidence_day2] == ["commit", "diff", "test"]
    assert "url" not in evidence_day2[0]
    assert evidence_day2[0]["ref"] == "cutoff-sha"

    day4 = _day_input(
        day_index=4,
        transcript_reference="transcript:44",
        transcript_segments=[
            {"startMs": 400},  # invalid, missing end
            {"startMs": 40, "endMs": 30, "content": "handoff reasoning"},
            {"start": 100, "end": 180, "excerpt": "fallback field"},
            "skip",
        ],
    )
    evidence_day4 = evaluator._build_day_evidence(day4)
    assert len(evidence_day4) == 2
    assert all(item["kind"] == "transcript" for item in evidence_day4)
    assert evidence_day4[0]["startMs"] == 40
    assert evidence_day4[0]["endMs"] == 40
    assert evidence_day4[0]["ref"] == "transcript:44"

    with_non_dict_segment = _day_input(
        day_index=4,
        transcript_reference="transcript:55",
        transcript_segments=[
            "skip",
            {"startMs": 1, "endMs": 2, "text": "valid"},
        ],
    )
    assert len(evaluator._build_day_evidence(with_non_dict_segment)) == 1

    fallback = evaluator._build_day_evidence(_day_input(day_index=99))
    assert fallback[0]["kind"] == "reflection"
    assert "No substantive evidence" in fallback[0]["excerpt"]


def test_score_for_day_variants():
    day1 = _day_input(
        day_index=1,
        content_text=None,
        content_json={"reflection": "strong narrative"},
    )
    score_day1 = evaluator._score_for_day(day1, evaluator._build_day_evidence(day1))
    assert 0 <= score_day1 <= 1

    day2 = _day_input(
        day_index=2,
        repo_full_name="acme/repo",
        commit_sha="abc",
        diff_summary={"base": "x", "head": "y"},
        tests_passed=None,
        tests_failed=None,
    )
    score_day2 = evaluator._score_for_day(day2, evaluator._build_day_evidence(day2))
    assert 0 <= score_day2 <= 1

    day4 = _day_input(
        day_index=4,
        transcript_reference="transcript:1",
        transcript_segments=[
            {"startMs": 1, "endMs": 2, "text": "Explained tradeoffs."}
        ],
    )
    score_day4 = evaluator._score_for_day(day4, evaluator._build_day_evidence(day4))
    assert score_day4 > 0


async def test_deterministic_evaluator_handles_empty_enabled_days():
    bundle = evaluator.EvaluationInputBundle(
        candidate_session_id=1,
        scenario_version_id=2,
        model_name="model-x",
        model_version="v1",
        prompt_version="p1",
        rubric_version="r1",
        disabled_day_indexes=[1],
        day_inputs=[_day_input(day_index=1, content_text="text")],
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
            _day_input(day_index=5, content_text="final reflection"),
            _day_input(
                day_index=2,
                repo_full_name="acme/repo",
                cutoff_commit_sha="cutoff-sha",
                diff_summary={"base": "a", "head": "b"},
                tests_passed=4,
                tests_failed=0,
                workflow_run_id="555",
            ),
        ],
    )

    result = await evaluator.get_fit_profile_evaluator().evaluate(bundle)
    assert [day.day_index for day in result.day_results] == [2, 5]
    assert 0 <= result.overall_fit_score <= 1
    assert 0 <= result.confidence <= 1
    assert result.report_json["version"]["modelVersion"] == "v2"
    assert result.report_json["dayScores"][0]["dayIndex"] == 2
