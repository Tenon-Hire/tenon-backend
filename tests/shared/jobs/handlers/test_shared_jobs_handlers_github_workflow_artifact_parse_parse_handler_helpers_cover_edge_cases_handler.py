from __future__ import annotations

from tests.shared.jobs.handlers.shared_jobs_handlers_github_workflow_artifact_parse_utils import *


def test_parse_handler_helpers_cover_edge_cases():
    assert parse_handler._parse_positive_int(True) is None
    assert parse_handler._parse_positive_int(0) is None
    assert parse_handler._parse_positive_int("0") is None
    assert parse_handler._parse_positive_int("-1") is None
    assert parse_handler._parse_positive_int("11") == 11

    assert parse_handler._parse_iso_datetime(None) is None
    assert parse_handler._parse_iso_datetime("  ") is None
    assert parse_handler._parse_iso_datetime("not-a-date") is None
    assert parse_handler._parse_iso_datetime("2026-03-13T14:00:00") == datetime(
        2026,
        3,
        13,
        14,
        0,
        tzinfo=UTC,
    )

    assert parse_handler._normalized_text(123) is None
    assert parse_handler._normalized_text("  hello  ") == "hello"
