from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_compose_report_prefers_scored_day_over_raw_placeholder():
    run = _run(
        overall_winoe_score=None,
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

    report = winoe_report_composer.compose_report(run)
    assert len(report["dayScores"]) == 1
    assert report["dayScores"][0]["dayIndex"] == 2
    assert report["dayScores"][0]["status"] == "scored"
    assert "disabledDayIndexes" not in report
