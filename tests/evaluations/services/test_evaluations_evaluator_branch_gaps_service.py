from __future__ import annotations

from app.evaluations.services import evaluator
from tests.evaluations.services.evaluations_evaluator_branch_gap_utils import day_input


def test_evaluator_day1_falls_back_to_content_json_excerpt_and_scores():
    day1 = day_input(
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
    day2 = day_input(
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
    day4 = day_input(
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
    assert (
        0
        <= evaluator._score_for_day(
            day_input(day_index=1, content_text=None, content_json=None), evidence=[]
        )
        <= 1
    )
    assert (
        0
        <= evaluator._score_for_day(
            day_input(day_index=2, tests_passed=1, tests_failed=1),
            evidence=[{"kind": "test"}],
        )
        <= 1
    )
    assert 0 <= evaluator._score_for_day(day_input(day_index=6), evidence=[]) <= 1
    day4 = day_input(
        day_index=4, transcript_segments=[{"startMs": 1, "endMs": 2, "text": "   "}]
    )
    assert 0 <= evaluator._score_for_day(day4, evidence=[]) <= 1


def test_evaluator_build_day_evidence_covers_optional_false_paths():
    evidence_day1 = evaluator._build_day_evidence(
        day_input(day_index=1, content_text=None, content_json=None)
    )
    assert evidence_day1[0]["kind"] == "reflection"
    evidence_day2 = evaluator._build_day_evidence(
        day_input(day_index=2, commit_sha=None, cutoff_commit_sha=None, diff_summary={})
    )
    assert evidence_day2[0]["kind"] in {"reflection", "test"}
    evidence_day4 = evaluator._build_day_evidence(
        day_input(
            day_index=4,
            transcript_segments=[{"startMs": 10, "endMs": 20, "text": "   "}],
        )
    )
    assert evidence_day4[0]["kind"] == "transcript"
    assert "excerpt" not in evidence_day4[0]
