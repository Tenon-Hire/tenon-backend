from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_compose_report_fallbacks_to_persisted_values_and_filters_metadata():
    run = _run(
        overall_winoe_score=None,
        recommendation=None,
        confidence=None,
        raw_report_json={
            "overallWinoeScore": 0.66,
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

    report = winoe_report_composer.compose_report(run)
    assert report["overallWinoeScore"] == 0.66
    assert report["confidence"] == 0.72
    assert report["recommendation"] == WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL
    assert report["disabledDayIndexes"] == [1, 2]
    assert report["dayScores"][0]["evidence"] == [{"kind": "commit", "ref": "abc"}]
