from __future__ import annotations

from app.evaluations.services import evaluator
from tests.evaluations.services.evaluations_evaluator_branch_gap_utils import day_input


def test_build_day_evidence_for_day2_day4_and_fallback():
    day2 = day_input(
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

    day4 = day_input(
        day_index=4,
        transcript_reference="transcript:44",
        transcript_segments=[
            {"startMs": 400},
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

    with_non_dict_segment = day_input(
        day_index=4,
        transcript_reference="transcript:55",
        transcript_segments=["skip", {"startMs": 1, "endMs": 2, "text": "valid"}],
    )
    assert len(evaluator._build_day_evidence(with_non_dict_segment)) == 1
    fallback = evaluator._build_day_evidence(day_input(day_index=99))
    assert fallback[0]["kind"] == "reflection"
    assert "No substantive evidence" in fallback[0]["excerpt"]


def test_score_for_day_variants():
    day1 = day_input(
        day_index=1, content_text=None, content_json={"reflection": "strong narrative"}
    )
    score_day1 = evaluator._score_for_day(day1, evaluator._build_day_evidence(day1))
    assert 0 <= score_day1 <= 1

    day2 = day_input(
        day_index=2,
        repo_full_name="acme/repo",
        commit_sha="abc",
        diff_summary={"base": "x", "head": "y"},
        tests_passed=None,
        tests_failed=None,
    )
    score_day2 = evaluator._score_for_day(day2, evaluator._build_day_evidence(day2))
    assert 0 <= score_day2 <= 1

    day4 = day_input(
        day_index=4,
        transcript_reference="transcript:1",
        transcript_segments=[
            {"startMs": 1, "endMs": 2, "text": "Explained tradeoffs."}
        ],
    )
    score_day4 = evaluator._score_for_day(day4, evaluator._build_day_evidence(day4))
    assert score_day4 > 0
