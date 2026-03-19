"""
GAP-FILLING TESTS: evaluator + scenario generation branch coverage

Targets:
- app/services/evaluations/evaluator.py
- app/services/simulations/scenario_generation.py
- app/services/evaluations/fit_profile_pipeline.py (transcript normalization branch)
"""

from __future__ import annotations

from app.services.evaluations import evaluator, fit_profile_pipeline
from app.services.simulations import scenario_generation


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


def test_evaluator_day1_falls_back_to_content_json_excerpt_and_scores():
    day1 = _day_input(
        day_index=1,
        content_text="   ",
        content_json={"narrative": "A clear design narrative."},
    )

    evidence = evaluator._build_day_evidence(day1)
    score = evaluator._score_for_day(day1, evidence)

    assert evidence[0]["kind"] == "reflection"
    assert evidence[0]["excerpt"]
    assert 0 <= score <= 1


def test_evaluator_day2_builds_commit_diff_test_evidence_and_scores():
    day2 = _day_input(
        day_index=2,
        repo_full_name="acme/repo",
        cutoff_commit_sha="cutoff-123",
        diff_summary={"base": "abc", "head": "def"},
        tests_passed=9,
        tests_failed=1,
        workflow_run_id="run-1",
    )

    evidence = evaluator._build_day_evidence(day2)
    kinds = {item["kind"] for item in evidence}
    score = evaluator._score_for_day(day2, evidence)

    assert {"commit", "diff", "test"} <= kinds
    assert score >= 0.08


def test_evaluator_day4_transcript_segments_include_excerpt_and_scoring_bonus():
    day4 = _day_input(
        day_index=4,
        transcript_reference="transcript:99",
        transcript_segments=[
            {
                "startMs": 10,
                "endMs": 25,
                "text": "Discussed tradeoffs and rollout plan.",
            }
        ],
    )

    evidence = evaluator._build_day_evidence(day4)
    score = evaluator._score_for_day(day4, evidence)

    assert evidence[0]["kind"] == "transcript"
    assert "excerpt" in evidence[0]
    assert score > 0.08


def test_evaluator_score_for_day_covers_false_paths():
    # Day 1/5 excerpt falsy path.
    day1 = _day_input(day_index=1, content_text=None, content_json=None)
    score_day1 = evaluator._score_for_day(day1, evidence=[])
    assert 0 <= score_day1 <= 1

    # Day 2/3 commit and diff missing, test evidence present.
    day2 = _day_input(day_index=2, tests_passed=1, tests_failed=1)
    score_day2 = evaluator._score_for_day(day2, evidence=[{"kind": "test"}])
    assert 0 <= score_day2 <= 1

    # Non-day-1/2/3/4 path (line 148 -> 156 arc).
    day6 = _day_input(day_index=6)
    score_day6 = evaluator._score_for_day(day6, evidence=[])
    assert 0 <= score_day6 <= 1

    # Day 4 transcript chars == 0 path.
    day4 = _day_input(
        day_index=4,
        transcript_segments=[{"startMs": 1, "endMs": 2, "text": "   "}],
    )
    score_day4 = evaluator._score_for_day(day4, evidence=[])
    assert 0 <= score_day4 <= 1


def test_evaluator_build_day_evidence_covers_optional_false_paths():
    # Day 1/5: excerpt missing -> no reflection evidence from content.
    day1 = _day_input(day_index=1, content_text=None, content_json=None)
    evidence_day1 = evaluator._build_day_evidence(day1)
    assert evidence_day1[0]["kind"] == "reflection"

    # Day 2/3: commit/diff optional values missing.
    day2 = _day_input(
        day_index=2, commit_sha=None, cutoff_commit_sha=None, diff_summary={}
    )
    evidence_day2 = evaluator._build_day_evidence(day2)
    assert evidence_day2[0]["kind"] in {"reflection", "test"}

    # Day 4: transcript excerpt is None, so no excerpt key.
    day4 = _day_input(
        day_index=4,
        transcript_segments=[{"startMs": 10, "endMs": 20, "text": "   "}],
    )
    evidence_day4 = evaluator._build_day_evidence(day4)
    assert evidence_day4[0]["kind"] == "transcript"
    assert "excerpt" not in evidence_day4[0]


def test_template_display_name_handles_blank_catalog_value(monkeypatch):
    monkeypatch.setattr(
        scenario_generation,
        "TEMPLATE_CATALOG",
        {"template-x": {"display_name": "   "}},
    )

    assert scenario_generation._template_display_name("template-x") == "template-x"


def test_apply_generated_task_updates_covers_invalid_and_blank_inputs():
    tasks = [
        type(
            "Task",
            (),
            {
                "day_index": 1,
                "title": "Original 1",
                "description": "Original 1",
                "max_score": 5,
            },
        )(),
        type(
            "Task",
            (),
            {
                "day_index": 2,
                "title": "Original 2",
                "description": "Original 2",
                "max_score": 7,
            },
        )(),
    ]

    scenario_generation.apply_generated_task_updates(
        tasks=tasks,
        task_prompts_json=[
            {"dayIndex": "bad", "title": "Ignore", "description": "Ignore"},
            {"dayIndex": -1, "title": "Ignore", "description": "Ignore"},
            {"dayIndex": 1, "title": "  ", "description": "  "},
            {"dayIndex": 2, "title": "Updated", "description": "Updated"},
        ],
        rubric_json={"dayWeights": {"abc": "x", "1": 0, "2": 20}},
    )

    assert tasks[0].title == "Original 1"
    assert tasks[0].description == "Original 1"
    assert tasks[0].max_score == 5
    assert tasks[1].title == "Updated"
    assert tasks[1].description == "Updated"
    assert tasks[1].max_score == 20


def test_apply_generated_task_updates_handles_non_dict_day_weights():
    task = type(
        "Task",
        (),
        {"day_index": 3, "title": "Title", "description": "Desc", "max_score": 9},
    )()

    scenario_generation.apply_generated_task_updates(
        tasks=[task],
        task_prompts_json=[],
        rubric_json={"dayWeights": ["not", "a", "dict"]},
    )

    assert task.max_score == 9


def test_normalize_transcript_segments_keeps_text_when_present():
    normalized = fit_profile_pipeline._normalize_transcript_segments(
        [{"startMs": 1, "endMs": 2, "text": "hello"}]
    )

    assert normalized == [{"startMs": 1, "endMs": 2, "text": "hello"}]


def test_normalize_transcript_segments_allows_missing_text():
    normalized = fit_profile_pipeline._normalize_transcript_segments(
        [{"startMs": 1, "endMs": 2, "text": "   "}]
    )

    assert normalized == [{"startMs": 1, "endMs": 2}]
