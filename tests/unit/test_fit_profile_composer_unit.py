from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

from app.repositories.evaluations.models import EVALUATION_RECOMMENDATION_LEAN_HIRE
from app.services.evaluations import fit_profile_composer


def _row(
    *,
    day_index: int,
    score: float,
    rubric_results_json=None,
    evidence_pointers_json=None,
):
    return SimpleNamespace(
        day_index=day_index,
        score=score,
        rubric_results_json=rubric_results_json,
        evidence_pointers_json=evidence_pointers_json,
    )


def _run(
    *,
    overall_fit_score=None,
    recommendation=None,
    confidence=None,
    raw_report_json=None,
    metadata_json=None,
    day_scores=None,
    generated_at=None,
    completed_at=None,
    started_at=None,
):
    return SimpleNamespace(
        overall_fit_score=overall_fit_score,
        recommendation=recommendation,
        confidence=confidence,
        raw_report_json=raw_report_json,
        metadata_json=metadata_json,
        day_scores=day_scores or [],
        model_name="fit-model",
        model_version="2026-03-12",
        prompt_version="fit-profile-v1",
        rubric_version="rubric-v1",
        generated_at=generated_at,
        completed_at=completed_at,
        started_at=started_at or datetime(2026, 3, 12, 12, 0),
    )


def test_fit_profile_composer_helper_normalizers():
    assert fit_profile_composer._normalize_datetime(None) is None
    normalized = fit_profile_composer._normalize_datetime(datetime(2026, 3, 12, 10, 0))
    assert normalized is not None
    assert normalized.tzinfo is not None
    aware = datetime(2026, 3, 12, 10, 0, tzinfo=timezone(timedelta(hours=-5)))
    utc_value = fit_profile_composer._normalize_datetime(aware)
    assert utc_value is not None
    assert utc_value.tzinfo == UTC

    assert fit_profile_composer._normalize_unit_interval(True) is None
    assert fit_profile_composer._normalize_unit_interval("0.3") is None
    assert fit_profile_composer._normalize_unit_interval(1.2) is None
    assert fit_profile_composer._normalize_unit_interval(0.33333) == 0.3333

    assert (
        fit_profile_composer._normalize_recommendation(None)
        == EVALUATION_RECOMMENDATION_LEAN_HIRE
    )
    assert fit_profile_composer._normalize_recommendation(" no_hire ") == "no_hire"
    assert (
        fit_profile_composer._normalize_recommendation("not-valid")
        == EVALUATION_RECOMMENDATION_LEAN_HIRE
    )


def test_fit_profile_composer_sanitize_evidence():
    assert fit_profile_composer._sanitize_evidence("bad") is None
    assert fit_profile_composer._sanitize_evidence({"kind": "   "}) is None
    assert fit_profile_composer._sanitize_evidence(
        {"kind": "commit", "ref": " x "}
    ) == {
        "kind": "commit",
        "ref": "x",
    }
    assert fit_profile_composer._sanitize_evidence(
        {
            "kind": "transcript",
            "ref": "t:1",
            "startMs": -1,
            "endMs": 20,
            "excerpt": " hello ",
        }
    ) == {
        "kind": "transcript",
        "ref": "t:1",
        "endMs": 20,
        "excerpt": "hello",
    }


def test_human_review_day_from_raw_rejects_invalid_shapes():
    assert fit_profile_composer._human_review_day_from_raw("bad") is None
    assert (
        fit_profile_composer._human_review_day_from_raw(
            {
                "dayIndex": True,
                "status": "human_review_required",
                "reason": "ai_eval_disabled_for_day",
            }
        )
        is None
    )
    assert (
        fit_profile_composer._human_review_day_from_raw(
            {
                "dayIndex": 6,
                "status": "human_review_required",
                "reason": "ai_eval_disabled_for_day",
            }
        )
        is None
    )
    assert (
        fit_profile_composer._human_review_day_from_raw(
            {
                "dayIndex": 4,
                "status": "human_review_required",
                "reason": "   ",
            }
        )
        is None
    )


def test_compose_report_fallbacks_to_persisted_values_and_filters_metadata():
    run = _run(
        overall_fit_score=None,
        recommendation=None,
        confidence=None,
        raw_report_json={
            "overallFitScore": 0.66,
            "confidence": 0.72,
            "recommendation": "definitely_maybe",
        },
        metadata_json={"disabledDayIndexes": [1, 2, "3", 8, 0]},
        day_scores=[
            _row(
                day_index=2,
                score=0.75,
                rubric_results_json={"quality": 0.75},
                evidence_pointers_json=[
                    {"kind": "commit", "ref": "abc"},
                    {"kind": ""},
                ],
            )
        ],
    )

    report = fit_profile_composer.compose_report(run)
    assert report["overallFitScore"] == 0.66
    assert report["confidence"] == 0.72
    assert report["recommendation"] == EVALUATION_RECOMMENDATION_LEAN_HIRE
    assert report["disabledDayIndexes"] == [1, 2]
    assert report["dayScores"][0]["evidence"] == [{"kind": "commit", "ref": "abc"}]


def test_compose_report_uses_day_score_mean_and_empty_defaults():
    run_with_scores = _run(
        overall_fit_score=None,
        confidence=None,
        raw_report_json={},
        day_scores=[
            _row(
                day_index=1,
                score=0.4,
                rubric_results_json={},
                evidence_pointers_json=[],
            ),
            _row(
                day_index=2,
                score=0.8,
                rubric_results_json={},
                evidence_pointers_json=[],
            ),
        ],
    )
    report = fit_profile_composer.compose_report(run_with_scores)
    assert report["overallFitScore"] == 0.6
    assert report["confidence"] == 0.0

    run_without_scores = _run(
        overall_fit_score=None,
        confidence=None,
        raw_report_json={},
        day_scores=[],
    )
    empty_report = fit_profile_composer.compose_report(run_without_scores)
    assert empty_report["overallFitScore"] == 0.0
    assert empty_report["confidence"] == 0.0


def test_compose_report_includes_human_review_placeholders_from_raw_report():
    run = _run(
        overall_fit_score=None,
        confidence=None,
        raw_report_json={
            "dayScores": [
                {
                    "dayIndex": 4,
                    "status": "human_review_required",
                    "reason": "ai_eval_disabled_for_day",
                }
            ]
        },
        metadata_json={},
        day_scores=[
            _row(
                day_index=2,
                score=0.8,
                rubric_results_json={},
                evidence_pointers_json=[],
            )
        ],
    )

    report = fit_profile_composer.compose_report(run)
    assert report["overallFitScore"] == 0.8
    assert report["disabledDayIndexes"] == [4]
    day4 = next(day for day in report["dayScores"] if day["dayIndex"] == 4)
    assert day4["status"] == "human_review_required"
    assert day4["reason"] == "ai_eval_disabled_for_day"
    assert day4["score"] is None


def test_compose_report_prefers_scored_day_over_raw_placeholder():
    run = _run(
        overall_fit_score=None,
        confidence=None,
        raw_report_json={
            "dayScores": [
                {
                    "dayIndex": 2,
                    "status": "human_review_required",
                    "reason": "ai_eval_disabled_for_day",
                }
            ]
        },
        metadata_json={},
        day_scores=[
            _row(
                day_index=2,
                score=0.7,
                rubric_results_json={},
                evidence_pointers_json=[],
            )
        ],
    )

    report = fit_profile_composer.compose_report(run)
    assert len(report["dayScores"]) == 1
    assert report["dayScores"][0]["dayIndex"] == 2
    assert report["dayScores"][0]["status"] == "scored"
    assert "disabledDayIndexes" not in report


def test_build_ready_payload_uses_started_at_when_other_timestamps_missing():
    run = _run(
        generated_at=None,
        completed_at=None,
        started_at=datetime(2026, 3, 12, 9, 0),
    )
    payload = fit_profile_composer.build_ready_payload(run)
    assert payload["status"] == "ready"
    assert payload["generatedAt"] is not None
    assert payload["generatedAt"].tzinfo is not None
