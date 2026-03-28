from __future__ import annotations

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_finalize_text_utils import *


def test_parse_helpers_cover_edge_cases() -> None:
    assert finalize_handler._parse_positive_int(True) is None
    assert finalize_handler._parse_positive_int("12") == 12
    assert finalize_handler._parse_positive_int("0") is None
    assert finalize_handler._parse_positive_int("12x") is None
    assert finalize_handler._parse_positive_int(-1) is None

    assert finalize_handler._parse_optional_datetime(123) is None
    assert finalize_handler._parse_optional_datetime("") is None
    assert finalize_handler._parse_optional_datetime("bad-iso") is None
    naive = finalize_handler._parse_optional_datetime("2026-03-10T18:30:00")
    assert naive is not None
    assert naive.tzinfo == UTC
