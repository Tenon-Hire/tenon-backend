from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


def test_winoe_report_pipeline_helper_parsing_and_hashes():
    assert winoe_report_pipeline._parse_positive_int(True) is None
    assert winoe_report_pipeline._parse_positive_int(-1) is None
    assert winoe_report_pipeline._parse_positive_int("7") == 7
    assert winoe_report_pipeline._safe_int(True) is None
    assert winoe_report_pipeline._safe_int(9) == 9
    assert winoe_report_pipeline._safe_int(9.8) == 9
    assert winoe_report_pipeline._segment_start_ms({"x": 1}) is None
    assert winoe_report_pipeline._segment_end_ms({"x": 1}) is None
    assert winoe_report_pipeline._parse_diff_summary(None) is None
    assert winoe_report_pipeline._parse_diff_summary("not-json") is None
    assert winoe_report_pipeline._parse_diff_summary("[1,2,3]") is None
    assert winoe_report_pipeline._parse_diff_summary('{"base":"a","head":"b"}') == {
        "base": "a",
        "head": "b",
    }
    assert winoe_report_pipeline._submission_basis_hash(None) is None
    assert winoe_report_pipeline._transcript_basis_hash(None) is None

    enabled, disabled = winoe_report_pipeline._normalize_day_toggles(
        {"2": False, "4": False}
    )
    assert enabled == [1, 3, 5]
    assert disabled == [2, 4]

    digest_one = winoe_report_pipeline._stable_hash({"x": 1, "y": [2, 3]})
    digest_two = winoe_report_pipeline._stable_hash({"y": [2, 3], "x": 1})
    assert digest_one == digest_two
