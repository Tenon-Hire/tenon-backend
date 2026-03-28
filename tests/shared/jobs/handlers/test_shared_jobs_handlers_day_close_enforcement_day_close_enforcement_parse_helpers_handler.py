from __future__ import annotations

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


def test_day_close_enforcement_parse_helpers():
    assert enforcement_handler._parse_positive_int(True) is None
    assert enforcement_handler._parse_positive_int(0) is None
    assert enforcement_handler._parse_positive_int(-1) is None
    assert enforcement_handler._parse_positive_int(3) == 3
    assert enforcement_handler._parse_positive_int("7") == 7
    assert enforcement_handler._parse_positive_int(" 7 ") is None
    assert enforcement_handler._parse_positive_int("abc") is None

    assert enforcement_handler._parse_optional_datetime(None) is None
    assert enforcement_handler._parse_optional_datetime("   ") is None
    assert enforcement_handler._parse_optional_datetime("not-a-date") is None
    assert enforcement_handler._parse_optional_datetime(
        "2026-03-08T12:00:00"
    ) == datetime(2026, 3, 8, 12, 0, tzinfo=UTC)
    assert enforcement_handler._parse_optional_datetime(
        "2026-03-08T12:00:00+02:00"
    ) == datetime(2026, 3, 8, 10, 0, tzinfo=UTC)

    assert enforcement_handler._to_iso_z(None) is None
    assert (
        enforcement_handler._to_iso_z(datetime(2026, 3, 8, 12, 0))
        == "2026-03-08T12:00:00Z"
    )
    assert (
        enforcement_handler._to_iso_z(datetime(2026, 3, 8, 12, 0, tzinfo=UTC))
        == "2026-03-08T12:00:00Z"
    )

    assert enforcement_handler._extract_head_sha({}) is None
    assert enforcement_handler._extract_head_sha({"commit": {}}) is None
    assert enforcement_handler._extract_head_sha({"commit": {"sha": "  "}}) is None
    assert enforcement_handler._extract_head_sha({"commit": {"sha": " abc "}}) == "abc"
