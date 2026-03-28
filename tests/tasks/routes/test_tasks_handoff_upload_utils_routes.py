from __future__ import annotations

from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_handoff_upload_utils as handoff_utils,
)


def test_coerce_optional_int_returns_none_for_non_digit_string():
    assert handoff_utils.coerce_optional_int(" 12a ") is None
    assert handoff_utils.coerce_optional_int(" ") is None


def test_serialize_transcript_segments_returns_empty_for_non_list_input():
    assert handoff_utils.serialize_transcript_segments({"text": "not-a-list"}) == []
