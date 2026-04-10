from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_compose_report_includes_human_review_placeholders_from_raw_report():
    run = _run(
        overall_winoe_score=None,
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

    report = winoe_report_composer.compose_report(run)
    assert report["overallWinoeScore"] == 0.8
    assert report["disabledDayIndexes"] == [4]
    day4 = next(day for day in report["dayScores"] if day["dayIndex"] == 4)
    assert day4["status"] == "human_review_required"
    assert day4["reason"] == "ai_eval_disabled_for_day"
    assert day4["score"] is None
