from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_winoe_report_composer_helper_normalizers():
    assert winoe_report_composer._normalize_datetime(None) is None
    normalized = winoe_report_composer._normalize_datetime(datetime(2026, 3, 12, 10, 0))
    assert normalized is not None
    assert normalized.tzinfo is not None
    aware = datetime(2026, 3, 12, 10, 0, tzinfo=timezone(timedelta(hours=-5)))
    utc_value = winoe_report_composer._normalize_datetime(aware)
    assert utc_value is not None
    assert utc_value.tzinfo == UTC

    assert winoe_report_composer._normalize_unit_interval(True) is None
    assert winoe_report_composer._normalize_unit_interval("0.3") is None
    assert winoe_report_composer._normalize_unit_interval(1.2) is None
    assert winoe_report_composer._normalize_unit_interval(0.33333) == 0.3333

    assert (
        winoe_report_composer._normalize_recommendation(None)
        == WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL
    )
    assert (
        winoe_report_composer._normalize_recommendation(" no_hire ")
        == WINOE_REPORT_RECOMMENDATION_LIMITED_SIGNAL
    )
    assert (
        winoe_report_composer._normalize_recommendation("not-valid")
        == WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL
    )
