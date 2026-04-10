from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_human_review_day_from_raw_rejects_invalid_shapes():
    assert winoe_report_composer._human_review_day_from_raw("bad") is None
    assert (
        winoe_report_composer._human_review_day_from_raw(
            {
                "dayIndex": True,
                "status": "human_review_required",
                "reason": "ai_eval_disabled_for_day",
            }
        )
        is None
    )
    assert (
        winoe_report_composer._human_review_day_from_raw(
            {
                "dayIndex": 6,
                "status": "human_review_required",
                "reason": "ai_eval_disabled_for_day",
            }
        )
        is None
    )
    assert (
        winoe_report_composer._human_review_day_from_raw(
            {
                "dayIndex": 4,
                "status": "human_review_required",
                "reason": "   ",
            }
        )
        is None
    )
