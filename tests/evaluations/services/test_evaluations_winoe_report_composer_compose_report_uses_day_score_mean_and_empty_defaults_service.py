from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_compose_report_uses_day_score_mean_and_empty_defaults():
    run_with_scores = _run(
        overall_winoe_score=None,
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
    report = winoe_report_composer.compose_report(run_with_scores)
    assert report["overallWinoeScore"] == 0.6
    assert report["confidence"] == 0.0

    run_without_scores = _run(
        overall_winoe_score=None,
        confidence=None,
        raw_report_json={},
        day_scores=[],
    )
    empty_report = winoe_report_composer.compose_report(run_without_scores)
    assert empty_report["overallWinoeScore"] == 0.0
    assert empty_report["confidence"] == 0.0
